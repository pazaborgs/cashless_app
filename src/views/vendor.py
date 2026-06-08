import streamlit as st
from supabase import Client
from utils.formatting import format_currency, parse_card_input
from utils.qr import scan_qr_from_camera

# TODO: Consertar horário nas transações

# ==============================================
# DATABASE HELPERS
# ==============================================


def _fetch_stats(supabase: Client, vendor_id: str) -> tuple[float, int]:
    """Retorna (total_vendido, qtd_transacoes) do vendedor."""
    query = (
        supabase.table("transactions")
        .select("value")
        .eq("id_seller", vendor_id)
        .eq("operation_type", "VENDA")
        .execute()
    )
    if not query.data:
        return 0.0, 0
    total = sum(float(r["value"]) for r in query.data)
    return total, len(query.data)


def _fetch_card(supabase: Client, card_id: str, token: str) -> dict | None:
    """Busca a ficha pelo par ID/Token. Retorna None se não encontrada."""
    query = (
        supabase.table("cards")
        .select("*")
        .eq("id_card", card_id)
        .eq("token", token)
        .execute()
    )
    return query.data[0] if query.data else None


def _fetch_transactions(supabase: Client, vendor_id: str) -> list[dict]:
    """Retorna as transações do vendedor, mais recentes primeiro."""
    query = (
        supabase.table("transactions")
        .select("id_card, value, created_at")
        .eq("id_seller", vendor_id)
        .eq("operation_type", "VENDA")
        .order("created_at", desc=True)
        .execute()
    )
    return query.data if query.data else []


def _do_sale(
    supabase: Client, card_id: str, vendor_id: str, amount: float, new_balance: float
) -> None:
    """Insere a transação e debita o saldo no banco."""
    supabase.table("transactions").insert(
        {
            "id_card": card_id,
            "id_seller": vendor_id,
            "operation_type": "VENDA",
            "value": amount,
        }
    ).execute()
    supabase.table("cards").update({"balance": new_balance}).eq(
        "id_card", card_id
    ).execute()


# ==============================================
# UI HELPERS
# ==============================================



def _render_stats(supabase: Client, vendor_id: str) -> None:
    """KPIs do vendedor no topo da página."""
    total, qty = _fetch_stats(supabase, vendor_id)
    st.markdown(
        f"""
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Terminal</div>
                <div class="kpi-value">{vendor_id}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Total Vendido</div>
                <div class="kpi-value">{format_currency(total)}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Vendas</div>
                <div class="kpi-value">{qty}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_input() -> str | None:
    """Leitura por câmera ou entrada manual. Retorna raw_input ou None."""
    st.markdown(
        '<div class="section-divider">Identificação da Ficha</div>',
        unsafe_allow_html=True,
    )

    col_cam, col_txt = st.columns([1, 1], gap="large")
    with col_cam:
        st.caption("📷 Câmera — aponte para o QR Code")
        cam = st.camera_input("Câmera", key="cam_vendor", label_visibility="collapsed")
    with col_txt:
        st.caption("⌨️ Entrada manual / leitor USB")
        txt = st.text_input(
            "Código da ficha",
            key="txt_vendor",
            placeholder="Ex.: 001-a8f2c9",
            label_visibility="collapsed",
        )

    # Prioriza texto; tenta câmera se campo vazio
    raw: str | None = txt.strip() or None
    if not raw and cam:
        decoded = scan_qr_from_camera(cam)
        if decoded:
            raw = decoded
            st.success("✅ QR Code lido com sucesso.")
        else:
            st.warning("⚠️ QR Code não identificado. Centralize a imagem e tente novamente.")

    # Persiste o último input válido para sobreviver ao rerun
    if raw:
        st.session_state["vendor_last_raw"] = raw

    if st.session_state.get("vendor_last_raw"):
        if st.button("✖ Limpar ficha", key="clear_vendor_input"):
            for key in ["vendor_last_raw", "vendor_cart", "vendor_pending_sale"]:
                st.session_state.pop(key, None)
            st.rerun()

    return st.session_state.get("vendor_last_raw")


def _render_menu(menu: list[dict], current_balance: float) -> None:
    """Cardápio com multi-seleção e carrinho acumulado."""

    # Bloqueia edição enquanto confirmação estiver aberta
    if st.session_state.get("vendor_pending_sale"):
        return

    if "vendor_cart" not in st.session_state:
        st.session_state["vendor_cart"] = []

    cart: list[dict] = st.session_state["vendor_cart"]
    cart_total = sum(i["price"] for i in cart)

    # Cardápio
    st.markdown(
        '<div class="section-divider">Cardápio</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    for i, item in enumerate(menu):
        price = float(item["price"])
        would_exceed = (cart_total + price) > current_balance
        label = f"{item['item']}\n{format_currency(price)}" + ("  ⚠️" if would_exceed else "")
        with cols[i % 2]:
            if st.button(label, key=f"menu_item_{i}", use_container_width=True):
                cart.append({"name": item["item"], "price": price})
                st.session_state["vendor_cart"] = cart
                st.rerun()

    # Carrinho
    st.markdown(
        '<div class="section-divider">Carrinho</div>',
        unsafe_allow_html=True,
    )

    if not cart:
        st.caption("Nenhum item selecionado.")
        return

    for idx, cart_item in enumerate(cart):
        col_name, col_price, col_remove = st.columns([5, 2, 1])
        with col_name:
            st.markdown(f"**{cart_item['name']}**")
        with col_price:
            st.markdown(format_currency(cart_item["price"]))
        with col_remove:
            if st.button("✖", key=f"remove_{idx}"):
                cart.pop(idx)
                st.session_state["vendor_cart"] = cart
                st.rerun()

    st.divider()

    cart_total = sum(i["price"] for i in cart)
    balance_after = current_balance - cart_total
    insufficient = cart_total > current_balance

    if insufficient:
        st.markdown(
            f"""
            <div class="access-denied">
                <h3>⚠️ Saldo insuficiente</h3>
                <p>Total do carrinho: {format_currency(cart_total)} —
                saldo disponível: {format_currency(current_balance)}.<br>
                Remova itens para continuar.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.caption(f"Total: {format_currency(cart_total)} · Saldo após venda: {format_currency(balance_after)}")


def _render_sale_confirmation(
    supabase: Client,
    vendor_id: str,
    card_id: str,
    current_balance: float,
) -> None:
    """Botão de venda + resumo de confirmação."""
    cart: list[dict] = st.session_state.get("vendor_cart", [])
    cart_total = sum(i["price"] for i in cart)
    insufficient = cart_total > current_balance
    pending = st.session_state.get("vendor_pending_sale")

    sell = st.button(
        f"✔ Confirmar Venda de {format_currency(cart_total)}",
        type="primary",
        use_container_width=True,
        disabled=(not cart or insufficient or bool(pending)),
        key="sell_btn",
    )

    if sell:
        st.session_state["vendor_pending_sale"] = {
            "card_id": card_id,
            "vendor_id": vendor_id,
            "cart": list(cart),
            "total": cart_total,
            "current_balance": current_balance,
            "new_balance": current_balance - cart_total,
        }
        st.rerun()

    # Resumo — só aparece após o primeiro clique
    pending = st.session_state.get("vendor_pending_sale")
    if not pending or pending["card_id"] != card_id:
        return

    items_html = ""
    for i in pending["cart"]:
        items_html += f'<div class="tx-row"><span class="tx-key">{i["name"]}</span><span>{format_currency(i["price"])}</span></div>'

    st.markdown(
        f"""
        <div class="tx-log">
            {items_html}
            <div class="tx-row"><span class="tx-key">TOTAL</span><span>{format_currency(pending['total'])}</span></div>
            <div class="tx-row"><span class="tx-key">FICHA</span><span>#{pending['card_id']}</span></div>
            <div class="tx-row"><span class="tx-key">SALDO ATUAL</span><span>{format_currency(pending['current_balance'])}</span></div>
            <div class="tx-row"><span class="tx-key">SALDO APÓS</span><span>{format_currency(pending['new_balance'])}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_ok, col_cancel = st.columns(2, gap="small")
    with col_ok:
        if st.button("✔ Confirmar", type="primary", use_container_width=True, key="confirm_yes"):
            _do_sale(
                supabase,
                pending["card_id"],
                pending["vendor_id"],
                pending["total"],
                pending["new_balance"],
            )
            st.success(f"✅ Venda de {format_currency(pending['total'])} debitada na ficha #{pending['card_id']}.")
            for key in ["vendor_last_raw", "vendor_cart", "vendor_pending_sale"]:
                st.session_state.pop(key, None)
            st.rerun()
    with col_cancel:
        if st.button("✖ Cancelar", use_container_width=True, key="confirm_no"):
            st.session_state.pop("vendor_pending_sale", None)
            st.rerun()


def _render_transactions(supabase: Client, vendor_id: str) -> None:
    """Histórico do dia em expander."""
    with st.expander("📋 Transações do dia"):
        transactions = _fetch_transactions(supabase, vendor_id)
        if not transactions:
            st.caption("Nenhuma transação registrada ainda.")
            return

        html = '<div class="tx-log">'
        for t in transactions:
            html += f"""
                <div class="tx-row">
                    <span class="tx-key">FICHA</span>
                    <span>#{t['id_card']}</span>
                </div>
                <div class="tx-row">
                    <span class="tx-key">VALOR</span>
                    <span>{format_currency(float(t['value']))}</span>
                </div>
                <div class="tx-row">
                    <span class="tx-key">HORÁRIO</span>
                    <span>{t['created_at'][11:16]}</span>
                </div>
                <div class="tx-row" style="border-bottom: 2px solid #999; margin-bottom: .4rem;"></div>
            """
        html += "</div>"

        st.iframe(
            f"""
            <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
            <style>
                body {{ margin: 0; background: transparent; }}
                .tx-log {{
                    background: #E8E6E1;
                    border: 1px solid #D9D7D1;
                    border-radius: 8px;
                    padding: 1rem 1.25rem;
                    font-family: 'IBM Plex Mono', monospace;
                    font-size: 0.8rem;
                    color: #1C1C1C;
                }}
                .tx-row {{
                    display: flex;
                    justify-content: space-between;
                    padding: 0.3rem 0;
                    border-bottom: 1px solid #D9D7D1;
                }}
                .tx-row:last-child {{ border-bottom: none; }}
                .tx-key {{ color: #888; }}
            </style>
            {html}
            """,
            height=len(transactions) * 120,
        )


# ==============================================
# ENTRY POINT
# ==============================================



def render_vendor(supabase: Client, vendor_id: str, menu: list[dict]) -> None:
    """Renderiza a view completa do vendedor."""
    from utils.components import render_topbar

    render_topbar("Ponto de Venda", vendor_id)
    st.markdown(
        f"""
        <div class="module-header">
            <h2>Ponto de Venda — {vendor_id}</h2>
            <p>Leia o QR Code da ficha do cliente para registrar a venda.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_stats(supabase, vendor_id)

    raw = _render_input()
    if not raw:
        _render_transactions(supabase, vendor_id)
        return

    parsed = parse_card_input(raw)
    if not parsed:
        st.error("❌ Formato inválido. O padrão esperado é `ID-Token` (ex.: `001-a8f2c9`).")
        _render_transactions(supabase, vendor_id)
        return

    card_id, token = parsed
    card = _fetch_card(supabase, card_id, token)

    if not card:
        st.markdown(
            """
            <div class="access-denied">
                <h3>⛔ Ficha não encontrada</h3>
                <p>O par ID/Token informado não está registrado no sistema.
                Verifique se a ficha é original e tente novamente.
                Em caso de dúvida, acione a supervisão do evento.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _render_transactions(supabase, vendor_id)
        return

    current_balance = float(card["balance"])

    # Dados da ficha
    st.markdown(
        '<div class="section-divider">Dados da Ficha</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="card-panel">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div class="kpi-label">Ficha Nº</div>
                    <div class="card-id">#{card_id}</div>
                </div>
                <span class="badge badge-success">✓ Validado</span>
            </div>
            <div style="margin-top:1rem;">
                <div class="kpi-label">Saldo Disponível</div>
                <div class="card-balance">{format_currency(current_balance)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_menu(menu, current_balance)
    _render_sale_confirmation(supabase, vendor_id, card_id, current_balance)
    _render_transactions(supabase, vendor_id)