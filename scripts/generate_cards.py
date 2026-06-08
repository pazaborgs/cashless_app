import csv
import os
import qrcode
import secrets


def generate_cards(
    total_cards: int = 100,
    qr_output_dir: str = "qrcodes",
    csv_filename: str = "data/load_cards.csv",
) -> None:
    """
    Gera tokens de segurança para cartões, cria seus respectivos QR Codes e
    exporta os dados estruturados para um arquivo CSV dentro do diretório 'data'.

    Args:
        total_cards (int): Quantidade de cartões a serem gerados.
        qr_output_dir (str): Caminho do diretório onde as imagens dos QR Codes serão salvas.
        csv_filename (str): Nome do arquivo CSV que será gerado dentro da pasta 'data'.
    """

    os.makedirs("data", exist_ok=True)
    os.makedirs(qr_output_dir, exist_ok=True)
    db_data = []

    print(f"Gerando {total_cards} cartões e QR Codes...")

    for i in range(1, total_cards + 1):
        card_id = f"{i:03d}"
        token = secrets.token_hex(3)
        qr_content = f"{card_id}-{token}"

        db_data.append([card_id, token, 0.00])

        # Configuração e geração do QR Code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_content)
        qr.make(fit=True)

        # Salvando a imagem do QR Code
        img = qr.make_image(fill_color="black", back_color="white")
        image_path = os.path.join(qr_output_dir, f"card_{card_id}.png")
        img.save(image_path)

    # Exportação dos dados para carga no banco
    with open(csv_filename, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["id_card", "token", "balance"])
        writer.writerows(db_data)

    print(f"Sucesso: {total_cards} cartões gerados em '{csv_filename}'.")


if __name__ == "__main__":
    generate_cards()
