"""Owner: M5. Tesseract OCR fallback (used when no Gemini Vision quota). Lazy imports."""


def ocr(image_bytes: bytes) -> str:
    from io import BytesIO

    import pytesseract
    from PIL import Image

    return pytesseract.image_to_string(Image.open(BytesIO(image_bytes)))
