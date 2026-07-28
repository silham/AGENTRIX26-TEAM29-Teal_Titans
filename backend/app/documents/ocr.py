"""Owner: M5. Tesseract OCR fallback for document text extraction.

Used when:
  - GEMINI_API_KEY is not set
  - Gemini 1.5 Flash free-tier quota is exhausted (GeminiQuotaExceeded)

Dependencies:
  - pytesseract  (wraps the system Tesseract binary)
  - Pillow       (image loading and pre-processing)
  - Tesseract binary must be installed on the host OS:
      Windows: https://github.com/UB-Mannheim/tesseract/wiki
      Ubuntu : sudo apt-get install tesseract-ocr
      macOS  : brew install tesseract
"""

from __future__ import annotations

import io
import logging
import os
import re

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

from app.schemas.document import DocumentType, VisionAnalysisResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tesseract config
# ---------------------------------------------------------------------------

_TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "")
if _TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD

_TESSERACT_LANG = os.environ.get("TESSERACT_LANG", "eng+sin+tam")


# ---------------------------------------------------------------------------
# Image pre-processing
# ---------------------------------------------------------------------------


def _preprocess_image(image: Image.Image) -> Image.Image:
    """Greyscale → upscale → contrast → sharpen for better OCR accuracy."""
    image = image.convert("L")
    min_dimension = 1000
    width, height = image.size
    if width < min_dimension or height < min_dimension:
        scale = max(min_dimension / width, min_dimension / height)
        image = image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
    image = ImageEnhance.Contrast(image).enhance(2.0)
    image = image.filter(ImageFilter.SHARPEN)
    return image


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


def extract_text(image_bytes: bytes) -> str:
    """Run Tesseract OCR on image_bytes and return extracted text."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        raise RuntimeError(f"Could not open image for OCR: {exc}") from exc

    try:
        processed = _preprocess_image(image)
    except Exception as exc:
        # Preprocessing is best-effort; a format PIL can open but not enhance
        # should still get a raw-OCR attempt rather than fail outright.
        logger.warning("Image preprocessing failed (%s); using raw image.", exc)
        processed = image

    try:
        text = pytesseract.image_to_string(processed, lang=_TESSERACT_LANG, config="--psm 6")
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract binary not found. "
            "Install Tesseract and set TESSERACT_CMD in your .env if needed."
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Tesseract OCR failed: {exc}") from exc

    logger.debug("Tesseract extracted %d characters.", len(text))
    return text.strip()


# ---------------------------------------------------------------------------
# Heuristic classifier
# ---------------------------------------------------------------------------

_TYPE_PATTERNS: dict[DocumentType, list[str]] = {
    DocumentType.NIC: [
        r"national identity",
        r"\bnic\b",
        r"identity card",
        r"sri lanka",
        r"identity number",
    ],
    DocumentType.PASSPORT: [
        r"\bpassport\b",
        r"republic of sri lanka",
        r"department of immigration",
        r"place of birth",
    ],
    DocumentType.BIRTH_CERTIFICATE: [
        r"birth certificate",
        r"date of birth",
        r"place of birth",
        r"registrar",
        r"born on",
    ],
    DocumentType.POLICE_REPORT: [
        r"police",
        r"officer in charge",
        r"station",
        r"report number",
        r"complaint",
    ],
    DocumentType.DRIVING_LICENSE: [
        r"driving licen",
        r"motor traffic",
        r"rmv",
        r"vehicle class",
    ],
    DocumentType.MARRIAGE_CERTIFICATE: [
        r"marriage certificate",
        r"married on",
        r"district registrar",
    ],
    DocumentType.DEATH_CERTIFICATE: [
        r"death certificate",
        r"deceased",
        r"date of death",
    ],
    DocumentType.APPLICATION_FORM: [
        r"application form",
        r"applicant",
        r"please fill",
        r"attach photograph",
    ],
}


def _classify_from_text(text: str) -> tuple[DocumentType, float]:
    text_lower = text.lower()
    scores: dict[DocumentType, int] = {}
    for doc_type, patterns in _TYPE_PATTERNS.items():
        count = sum(1 for p in patterns if re.search(p, text_lower))
        if count > 0:
            scores[doc_type] = count
    if not scores:
        return DocumentType.UNKNOWN, 0.0
    best_type = max(scores, key=lambda t: scores[t])
    confidence = min(scores[best_type] / len(_TYPE_PATTERNS[best_type]), 1.0)
    return best_type, round(confidence, 2)


def _detect_issues(text: str, expected_name: str) -> list[str]:
    issues: list[str] = []
    if len(text.strip()) < 20:
        issues.append("Image is too blurry or low-quality for text extraction.")
    if re.search(r"expir", text.lower()):
        issues.append("Document may be expired — please verify the validity date.")
    return issues


# ---------------------------------------------------------------------------
# Public high-level function (same output shape as gemini_vision)
# ---------------------------------------------------------------------------


def classify_from_ocr_text(
    image_bytes: bytes,
    expected_name: str = "document",
) -> VisionAnalysisResult:
    """
    OCR fallback: run Tesseract on image_bytes and return a VisionAnalysisResult.
    Called when Gemini quota is exhausted.
    """
    try:
        text = extract_text(image_bytes)
    except RuntimeError as exc:
        logger.error("OCR extraction failed: %s", exc)
        return VisionAnalysisResult(
            detected_type=DocumentType.UNKNOWN,
            extracted_text="",
            issues=["OCR could not process this image. Please upload a clearer scan or photo."],
            confidence=0.0,
        )

    detected_type, confidence = _classify_from_text(text)
    issues = _detect_issues(text, expected_name)

    logger.info(
        "OCR classified document as %s (confidence=%.2f, issues=%d)",
        detected_type,
        confidence,
        len(issues),
    )

    return VisionAnalysisResult(
        detected_type=detected_type,
        extracted_text=text,
        issues=issues,
        confidence=confidence,
    )


# Alias: matches scaffold's simple `ocr()` function signature
def ocr(image_bytes: bytes) -> str:
    """Simple OCR extraction — returns raw text string."""
    from io import BytesIO
    return pytesseract.image_to_string(Image.open(BytesIO(image_bytes)))
