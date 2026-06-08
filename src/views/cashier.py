import streamlit as st
from supabase import Client
from utils.formatting import format_currency, parse_card_input
from utils.qr import scan_qr_from_camera
from utils.components import render_topbar


# ==============================================
# DATABASE HELPERS
# ==============================================


def _fetch_stats(supabase: Client, cashier_id: str) -> tuple[float, int]:
    """Retorna (total_recarregado, qtd_operacoes) do caixa."""
    query = (
        supabase.table("transactions")
        .select("value")
        .eq("id_seller", f"Caixa {cashier_id}")
        .eq("operation_type", "RECARGA")
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


def _do_recharge(
    supabase: Client, card_id: str, cashier_id: str, amount: float, new_balance: float
) -> None:
    """Insere a transação e atualiza o saldo no banco."""
    supabase.table("transactions").insert(
        {
            "id_card": card_id,
            "id_seller": f"Caixa {cashier_id}",
            "operation_type": "RECARGA",
            "value": amount,
        }
    ).execute()
    supabase.table("cards").update({"balance": new_balance}).eq(
        "id_card", card_id
    ).execute()


# ==============================================
# UI RENDERS
# ==============================================


def _render_stats(supabase: Client, cashier_id: str) -> None:
    """KPIs do terminal no topo da página."""
    total, qtd = _fetch_stats(supabase, cashier_id)
    st.markdown(
        f"""
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Terminal</div>
                <div class="kpi-value">{cashier_id}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Total Recarregado</div>
                <div class="kpi-value">{format_currency(total)}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Operações</div>
                <div class="kpi-value">{qtd}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_input() -> str | None:
    """Leitura por câmera ou entrada manual. Retorna o raw_input ou None."""
    st.markdown(
        '<div class="section-divider">Identificação da Ficha</div>',
        unsafe_allow_html=True,
    )

    col_cam, col_txt = st.columns([1, 1], gap="large")
    with col_cam:
        st.caption("📷 Câmera — aponte para o QR Code")
        cam = st.camera_input("Câmera", key="cam_cashier", label_visibility="collapsed")
    with col_txt:
        st.caption("⌨️ Entrada manual / leitor USB")
        txt = st.text_input(
            "Código da ficha",
            key="txt_cashier",
            placeholder="Ex.: 001-a8f2c9",
            label_visibility="collapsed",
        )

    # Prioriza texto. Tenta câmera se campo vazio
    raw: str | None = txt.strip() or None
    if not raw and cam:
        decoded = scan_qr_from_camera(cam)
        if decoded:
            raw = decoded
            st.success("✅ QR Code lido com sucesso.")
        else:
            st.warning(
                "⚠️ QR Code não identificado. Centralize a imagem e tente novamente."
            )

    # Persiste o último input válido
    if raw:
        st.session_state["last_raw_input"] = raw

    return st.session_state.get("last_raw_input")


def _render_card_and_recharge(
    supabase: Client, cashier_id: str, card_id: str, token: str
) -> None:
    """Exibe os dados da ficha e executa a recarga."""
    card = _fetch_card(supabase, card_id, token)

    if not card:
        st.markdown(
            """
            <div class="access-denied">
                <h3>Ficha não encontrada</h3>
                <p>O par ID/Token informado não está registrado no sistema.
                Verifique se a ficha é original e tente novamente.
                Em caso de dúvida, acione a supervisão do evento.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    current_balance = float(card["balance"])

    # Exibe ficha

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

    # Formulário de recarga

    st.markdown(
        '<div class="section-divider">Carregar Créditos</div>',
        unsafe_allow_html=True,
    )

    col_val, col_btn = st.columns([2, 1], gap="medium")
    with col_val:
        amount = st.number_input(
            "Valor da recarga (R$)",
            min_value=1.0,
            max_value=500.0,
            step=5.0,
            value=20.0,
            key="recharge_amount",
            format="%.2f",
        )
        new_balance = current_balance + amount
        st.caption(f"Novo saldo após recarga: **{format_currency(new_balance)}**")

    with col_btn:
        st.markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)
        confirm = st.button(
            f"✔ Confirmar Recarga de {format_currency(amount)}",
            type="primary",
            use_container_width=True,
        )

    # Confirma e registra
    # Primeiro clique — abre o resumo de confirmação
    if confirm:
        st.session_state["pending_recharge"] = {
            "card_id": card_id,
            "cashier_id": cashier_id,
            "amount": amount,
            "current_balance": current_balance,
            "new_balance": new_balance,
        }
 
    # Resumo + confirm/cancel — só aparece após o primeiro clique
    pending = st.session_state.get("pending_recharge")
    if pending and pending["card_id"] == card_id:
        st.markdown(
            f"""
            <div class="tx-log">
                <div class="tx-row"><span class="tx-key">FICHA</span><span>#{pending['card_id']}</span></div>
                <div class="tx-row"><span class="tx-key">VALOR</span><span>{format_currency(pending['amount'])}</span></div>
                <div class="tx-row"><span class="tx-key">SALDO ATUAL</span><span>{format_currency(pending['current_balance'])}</span></div>
                <div class="tx-row"><span class="tx-key">SALDO APÓS</span><span>{format_currency(pending['new_balance'])}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
 
        col_ok, col_cancel = st.columns(2, gap="small")
        with col_ok:
            if st.button("✔ Confirm", type="primary", use_container_width=True, key="confirm_yes"):
                _do_recharge(
                    supabase,
                    pending["card_id"],
                    pending["cashier_id"],
                    pending["amount"],
                    pending["new_balance"],
                )
                st.session_state.pop("pending_recharge", None)
                st.session_state.pop("last_raw_input", None)
                st.success(f"✅ Recarga de {format_currency(pending['amount'])} creditada na ficha #{pending['card_id']}.")
                st.rerun()
        with col_cancel:
            if st.button("✖ Cancelar", use_container_width=True, key="confirm_no"):
                st.session_state.pop("pending_recharge", None)
                st.rerun()


# ==============================================
# ENTRYPOINT
# ==============================================


def render_cashier(supabase: Client, cashier_id: str) -> None:
    """Renderiza a view completa do caixa."""
    render_topbar("Recarga de Créditos", cashier_id)
    st.markdown(
        """
        <div class="module-header">
            <h2>Recarga de Créditos</h2>
            <p>Leia o QR Code da ficha do participante para consultar e recarregar o saldo.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_stats(supabase, cashier_id)

    raw = _render_input()
    if not raw:
        return

    parsed = parse_card_input(raw)
    if not parsed:
        st.error(
            "Formato inválido. O padrão esperado é `ID-Token` (ex.: `001-a8f2c9`)."
        )
        return

    card_id, token = parsed
    _render_card_and_recharge(supabase, cashier_id, card_id, token)
