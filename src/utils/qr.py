import cv2
import numpy as np


def scan_qr_from_camera(img_file_buffer) -> str | None:
    """Extrai e decodifica o QR Code da imagem capturada pela câmera."""
    if img_file_buffer is None:
        return None
    bytes_data = img_file_buffer.getvalue()
    cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(cv2_img)
    return data or None
