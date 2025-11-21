import base64
from io import BytesIO

import qrcode


def _tlv(tag: str, value: str) -> str:
    """Encode tag-length-value blocks as defined by the PromptPay EMV spec."""
    length = str(len(value)).zfill(2)
    return f"{tag}{length}{value}"


def crc16_ccitt(data: bytes) -> int:
    """CRC-16/CCITT-FALSE implementation (poly=0x1021, init=0xFFFF)."""
    poly = 0x1021
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) & 0xFFFF) ^ poly
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF


def generate_promptpay_payload(
    pp_id: str,
    amount: float | None = None,
    merchant_name: str = "MERCHANT",
    merchant_city: str = "BANGKOK",
) -> str:
    """Build an EMV PromptPay payload string."""
    payload = ""
    payload += _tlv("00", "01")
    payload += _tlv("01", "12" if amount else "11")

    merchant_account = _tlv("00", "A000000677010111")
    merchant_account += _tlv("01", pp_id)
    payload += _tlv("29", merchant_account)

    payload += _tlv("52", "0000")
    payload += _tlv("53", "764")
    if amount:
        payload += _tlv("54", f"{amount:.2f}")
    payload += _tlv("58", "TH")
    payload += _tlv("59", (merchant_name or "MERCHANT")[:25])
    payload += _tlv("60", (merchant_city or "CITY")[:15])

    payload_for_crc = payload + "6304"
    crc = crc16_ccitt(payload_for_crc.encode("utf-8"))
    payload += "63" + "04" + format(crc, "04X")
    return payload


def promptpay_qr_base64(
    pp_id: str,
    amount: float | None = None,
    merchant_name: str = "MERCHANT",
    merchant_city: str = "BANGKOK",
) -> tuple[str, str]:
    """Return (base64 PNG, payload) for the PromptPay QR."""
    payload = generate_promptpay_payload(pp_id, amount, merchant_name, merchant_city)
    img = qrcode.make(payload)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii"), payload

