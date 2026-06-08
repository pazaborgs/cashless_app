import streamlit as st
from supabase import create_client, Client


def test_connection() -> None:
    """
    Testa a conexão com o Supabase executando um SELECT e um INSERT.
    """

    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]

    try:
        supabase: Client = create_client(supabase_url, supabase_key)

        # Leitura (SELECT)

        print("Buscando dados do cartão '001'...")
        res_select = supabase.table("cards").select("*").eq("id_card", "001").execute()
        print(f"Resultado: {res_select.data}")

        # Escrita (INSERT)
        print("\nInserindo transação de teste...")
        mock_tx = {"id_card": "001", "operation_type": "VENDA", "value": 12.50}
        res_insert = supabase.table("transactions").insert(mock_tx).execute()
        print(f"Sucesso: {bool(res_insert.data)}")

    except Exception as e:
        print(f"\nFalha no teste de banco: {e}")


if __name__ == "__main__":
    print("Iniciando teste de conexão...\n")
    test_connection()
