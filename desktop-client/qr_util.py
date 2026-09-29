"""Generates the pairing QR code image encoding connection info as JSON."""
import json

import qrcode
from PIL import Image


def make_pairing_qr(ip: str, port: int, token: str, device_name: str) -> Image.Image:
    payload = {
        "v": 1,
        "ip": ip,
        "port": port,
        "token": token,
        "device_name": device_name,
    }
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(json.dumps(payload))
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")
