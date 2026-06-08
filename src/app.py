import streamlit as st
from datetime import datetime
from config_loader import load_all
from utils.styling import load_css
import hmac
from utils.database import get_supabase
from views.cashier import render_cashier
from views.vendor import render_vendor
from views.denied import render_denied

# ==============================================
# CONFIGURAÇÃO DE PÁGINA
# ==============================================

st.set_page_config(
    page_title="Cashless App",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==============================================
# ESTILOS GLOBAIS
# ==============================================


if "theme" not in st.session_state:
    st.session_state.theme = "dark"

load_css(st.session_state.theme)

# ==============================================
# SUPABASE
# ==============================================


supabase = get_supabase()


# ==============================================
# AUTENTICAÇÃO E CONFIG
# ==============================================


@st.cache_data(ttl=600)
def load_auth_data() -> dict:
    """Carrega caixas, vendedores e cardápios do Google Sheets (cache 10 min)."""
    return load_all()


config = load_auth_data()
AUTHORIZED_CASHIERS: dict[str, str] = config["cashiers"]
AUTHORIZED_VENDORS: dict[str, str] = config["vendors"]
VENDOR_MENU: dict[str, list] = config["menus"]


# ==============================================
# ROTEAMENTO (QUERY PARAMS)
# ==============================================

cashier_param = st.query_params.get("cashier")
vendor_param = st.query_params.get("vendor")
token_param = st.query_params.get("token")


is_cashier = cashier_param in AUTHORIZED_CASHIERS and hmac.compare_digest(
    AUTHORIZED_CASHIERS[cashier_param], token_param or ""
)
is_vendor = (
    vendor_param in AUTHORIZED_VENDORS
    and AUTHORIZED_VENDORS[vendor_param] == token_param
)

# ==============================================
# VIEWS
# ==============================================

if is_cashier:
    render_cashier(supabase, cashier_param)
elif is_vendor:
    menu = VENDOR_MENU.get(vendor_param, [])
    render_vendor(supabase, vendor_param, menu)
else:
    render_denied()
