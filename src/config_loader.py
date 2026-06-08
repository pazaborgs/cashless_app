import csv
import io
import time
import urllib.request
from typing import TypedDict

import streamlit as st

SHEET_ID = st.secrets["SHEET_ID"]
CACHE_TTL = 300  # segundos (5 min)

_cache: dict = {}
_cache_ts: float = 0


# ==============================================
# HELPERS
# ==============================================


def _csv_url(sheet_nome: str) -> str:
    """Monta a URL de exportação CSV de uma aba do Google Sheets."""
    return (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
        f"/gviz/tq?tqx=out:csv&sheet={sheet_nome}"
    )


def _fetch_csv(sheet_nome: str) -> list[dict]:
    """Busca e parseia o CSV de uma aba do Google Sheets."""
    url = _csv_url(sheet_nome)
    with urllib.request.urlopen(url, timeout=10) as resp:
        content = resp.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    return [row for row in reader]


# ==============================================
# DATA TYPES
# ==============================================


class MenuItem(TypedDict):
    item: str
    preco: float
    descricao: str


# ==============================================
# LOADERS
# ==============================================


def load_cashiers() -> dict[str, str]:
    """Retorna {nome: token} dos caixas autorizados."""
    rows = _fetch_csv("caixas")
    return {r["nome"]: r["token"] for r in rows if r.get("nome")}


def load_vendors() -> dict[str, str]:
    """Retorna {nome: token} dos vendedores autorizados."""
    rows = _fetch_csv("vendedores")
    return {r["nome"]: r["token"] for r in rows if r.get("nome")}


def load_menus() -> dict[str, list[MenuItem]]:
    """Retorna {vendedor: [{item, price, description}, ...]}."""
    rows = _fetch_csv("cardapios")
    menus: dict[str, list[MenuItem]] = {}
    for r in rows:
        vendor = r.get("vendedor", "").strip()
        item = r.get("item", "").strip()
        price_raw = r.get("preco", "").strip()

        if not vendor or not item or not price_raw:
            continue

        menus.setdefault(vendor, []).append(
            {
                "item": item,
                "price": float(price_raw),
                "description": r.get("descricao", "").strip(),
            }
        )
    return menus


def load_all() -> dict:
    """Carrega caixas, vendedores e cardápios do Google Sheets."""
    return {
        "cashiers": load_cashiers(),
        "vendors": load_vendors(),
        "menus": load_menus(),
    }


# ==============================================
# TESTE LOCAL
# ==============================================

if __name__ == "__main__":
    print("Carregando configurações do Sheets...\n")
    try:
        config = load_all()
        print(f"Caixas:     {list(config['cashiers'].keys())}")
        print(f"Vendedores: {list(config['vendors'].keys())}")
        print(f"Cardápios:  {list(config['menus'].keys())}")
    except Exception as e:
        print(f"\nFalha ao carregar configurações: {e}")
