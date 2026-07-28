"""Owner: M5. Gemini 1.5 Flash vision wrapper.

Responsibilities:
- Send uploaded document image to Gemini Vision
- Extract document type, visible fields, and potential issues
- Return a structured VisionAnalysisResult
- Raise GeminiQuotaExceeded so caller can fall back to Tesseract OCR
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings
from app.schemas.document import DocumentType, VisionAnalysisResult

logger = logging.getLogger(__name__)

# gemini-1.5-flash was retired by Google; 2.5-flash is the current free-tier vision model.
MODEL = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class GeminiQuotaExceeded(Exception):
    """Raised when Gemini free-tier quota is exhausted — caller must use OCR fallback."""


class GeminiVisionError(Exception):
    """Raised for unexpected Gemini API errors."""


# ---------------------------------------------------------------------------
# Document type mapping: Gemini free-text label → our enum
# ---------------------------------------------------------------------------

_TYPE_MAP: dict[str, DocumentType] = {
    "nic": DocumentType.NIC,
    "national identity card": DocumentType.NIC,
    "national id": DocumentType.NIC,
    "passport": DocumentType.PASSPORT,
    "birth certificate": DocumentType.BIRTH_CERTIFICATE,
    "police report": DocumentType.POLICE_REPORT,
    "police clearance": DocumentType.POLICE_REPORT,
    "driving license": DocumentType.DRIVING_LICENSE,
    "driving licence": DocumentType.DRIVING_LICENSE,
    "marriage certificate": DocumentType.MARRIAGE_CERTIFICATE,
    "death certificate": DocumentType.DEATH_CERTIFICATE,
    "application form": DocumentType.APPLICATION_FORM,
    "form": DocumentType.APPLICATION_FORM,
    "passport photo": DocumentType.PHOTO,
    "photograph": DocumentType.PHOTO,
    "photo": DocumentType.PHOTO,
}


def _map_document_type(raw_label: str) -> DocumentType:
    normalised = raw_label.strip().lower()
    for key, doc_type in _TYPE_MAP.items():
        if key in normalised:
            return doc_type
    return DocumentType.UNKNOWN


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_ANALYSIS_PROMPT = """
You are a Sri Lankan government document verification assistant.
Analyse the provided document image and respond ONLY with valid JSON — no markdown, no explanation.

The JSON must have exactly these keys:
{{
  "document_type": "<NIC | Passport | Birth Certificate | Police Report | Driving License | Passport Photo | Application Form | Other | Unknown>",
  "visible_fields": {{"<field label>": "<value or not visible>"}},
  "issues": ["<issue 1>", "<issue 2>"],
  "confidence": <float 0.0–1.0>,
  "extracted_text": "<all readable text joined by spaces>"
}}

Context: The citizen says this document is: "{expected_name}"

Add to "issues" if any of the following apply:
- Image is blurry or unreadable
- Document appears expired (check visible dates)
- Required signature is missing or illegible
- Photo background is not plain white or light blue (for passport photo)
- Document type does not match what the citizen claimed
- Required field is blank or obscured
- Photograph on document is missing or damaged (NIC / Passport)
- Seal or stamp is missing (certificates / police reports)

Return an empty "issues" list if the document looks fully valid.
"""


# ---------------------------------------------------------------------------
# Core public functions
# ---------------------------------------------------------------------------


def analyze_image(image_bytes: bytes, prompt: str, mime_type: str = "image/png") -> str:
    """Low-level call: send raw bytes + prompt, return raw text. Used by scaffold tests."""
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(MODEL)
    resp = model.generate_content([prompt, {"mime_type": mime_type, "data": image_bytes}])
    return resp.text


async def analyze_document(
    image_bytes: bytes,
    expected_name: str = "document",
    mime_type: str = "image/jpeg",
) -> VisionAnalysisResult:
    """
    Send image_bytes to Gemini 1.5 Flash and return a structured analysis.

    Raises:
        GeminiQuotaExceeded: when free-tier quota is exhausted (caller should use OCR).
        GeminiVisionError:   for other unexpected API failures.
    """
    import base64

    import google.generativeai as genai
    from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

    if not settings.gemini_api_key:
        raise GeminiVisionError(
            "GEMINI_API_KEY is not set. Add it to your .env file and restart the server."
        )

    genai.configure(api_key=settings.gemini_api_key)

    prompt = _ANALYSIS_PROMPT.format(expected_name=expected_name)
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    model = genai.GenerativeModel(MODEL)

    try:
        response = model.generate_content(
            [{"mime_type": mime_type, "data": b64_image}, prompt],
            generation_config=genai.GenerationConfig(temperature=0.1, max_output_tokens=1024),
        )
    except ResourceExhausted as exc:
        logger.warning("Gemini quota exhausted — caller should use OCR fallback: %s", exc)
        raise GeminiQuotaExceeded("Gemini 1.5 Flash free-tier quota exhausted.") from exc
    except ServiceUnavailable as exc:
        raise GeminiVisionError(f"Gemini service unavailable: {exc}") from exc
    except Exception as exc:
        raise GeminiVisionError(f"Unexpected Gemini error: {exc}") from exc

    raw_text = response.text.strip()
    logger.debug("Gemini raw response: %s", raw_text)
    return _parse_gemini_response(raw_text)


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------


def _parse_gemini_response(raw_text: str) -> VisionAnalysisResult:
    """Parse Gemini's JSON response into a VisionAnalysisResult."""
    cleaned = raw_text
    if cleaned.startswith("```"):
        cleaned = "\n".join(
            line for line in cleaned.splitlines() if not line.startswith("```")
        )

    try:
        data: dict[str, Any] = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Gemini JSON: %s\nRaw: %s", exc, raw_text)
        return VisionAnalysisResult(
            detected_type=DocumentType.UNKNOWN,
            extracted_text=raw_text,
            issues=["Could not parse AI response — please re-upload a clearer image."],
            confidence=0.0,
            raw_response=raw_text,
        )

    return VisionAnalysisResult(
        detected_type=_map_document_type(data.get("document_type", "")),
        extracted_text=data.get("extracted_text", ""),
        visible_fields=data.get("visible_fields", {}),
        issues=data.get("issues", []),
        confidence=float(data.get("confidence", 0.5)),
        raw_response=raw_text,
    )


# ---------------------------------------------------------------------------
# Utility: translate text via Gemini (Sinhala / Tamil / English)
# ---------------------------------------------------------------------------


async def translate_text(text: str, target_language: str = "si") -> str:
    """Translate text to Sinhala ('si') or Tamil ('ta') using Gemini."""
    import google.generativeai as genai

    if target_language == "en" or not settings.gemini_api_key:
        return text

    lang_name = {"si": "Sinhala", "ta": "Tamil"}.get(target_language, "Sinhala")
    prompt = (
        f"Translate the following text to {lang_name}. "
        f"Return only the translated text, nothing else.\n\n{text}"
    )

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(MODEL)
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as exc:
        logger.warning("Translation failed, returning original: %s", exc)
        return text
