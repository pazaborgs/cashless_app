def parse_card_input(raw: str) -> tuple[str, str] | None:
    """Valida e quebra a string 'ID-Token'. Retorna None se inválido."""
    parts = raw.strip().split("-")
    if len(parts) == 2 and all(parts):
        return parts[0], parts[1]
    return None


def format_currency(value: float) -> str:
    """Formata valor float para o padrão brasileiro (R$ 1.234,56)."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
