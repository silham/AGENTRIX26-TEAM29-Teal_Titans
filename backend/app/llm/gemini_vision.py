"""Owner: M5. Gemini 1.5 Flash vision wrapper. Lazy imports."""
from app.config import settings

MODEL = "gemini-1.5-flash"


def analyze_image(image_bytes: bytes, prompt: str, mime_type: str = "image/png") -> str:
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(MODEL)
    resp = model.generate_content([prompt, {"mime_type": mime_type, "data": image_bytes}])
    return resp.text
    # TODO(M5): structured JSON output + Tesseract fallback (app.documents.ocr).
