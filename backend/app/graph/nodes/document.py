"""Owner: M5. Document graph node — Gemini Vision / Tesseract verification.

This node is invoked inside the LangGraph workflow after a document is uploaded.
It reads pending documents from GraphState, verifies each one via Gemini Vision
(with Tesseract OCR as a quota-safe fallback), and returns updated document dicts
to merge back into GraphState.
"""

from __future__ import annotations

import asyncio
import logging

from app.graph.state import GraphState
from app.llm.gemini_vision import GeminiQuotaExceeded, GeminiVisionError, analyze_document
from app.schemas.document import DocumentStatus, DocumentType

logger = logging.getLogger(__name__)


def _determine_status(detected_type: DocumentType, issues: list[str]) -> str:
    """Convert vision analysis result into a document status string."""
    if not issues:
        return DocumentStatus.ACCEPTED.value
    # If type is completely unknown, reject outright
    if detected_type == DocumentType.UNKNOWN:
        return DocumentStatus.REJECTED.value
    # Issues present but type recognised → incomplete
    return DocumentStatus.INCOMPLETE.value


async def _verify_one(doc: dict) -> dict:
    """Verify a single document dict and return an updated copy."""
    image_bytes: bytes | None = doc.get("_image_bytes")
    expected_name: str = doc.get("name", "document")
    mime_type: str = doc.get("_mime_type", "image/jpeg")

    if image_bytes is None:
        # No bytes attached — cannot verify yet
        return {**doc, "status": DocumentStatus.NEEDS_VERIFICATION.value}

    try:
        result = await analyze_document(image_bytes, expected_name=expected_name, mime_type=mime_type)
    except GeminiQuotaExceeded:
        logger.warning("Gemini quota exceeded — falling back to Tesseract OCR for '%s'", expected_name)
        from app.documents.ocr import classify_from_ocr_text

        result = classify_from_ocr_text(image_bytes, expected_name=expected_name)
    except GeminiVisionError as exc:
        logger.error("Gemini Vision error for '%s': %s", expected_name, exc)
        result = None

    if result is None:
        return {**doc, "status": DocumentStatus.NEEDS_VERIFICATION.value, "issues": ["Vision service unavailable."]}

    status = _determine_status(result.detected_type, result.issues)

    return {
        **doc,
        "detected_type": result.detected_type.value,
        "status": status,
        "issues": result.issues,
        "confidence": result.confidence,
        "extracted_text": result.extracted_text,
        # Remove internal bytes from state — they don't serialise
        "_image_bytes": None,
    }


def document(state: GraphState) -> dict:
    """
    Document Verification node.

    Reads `state["documents"]`, verifies any that have `_image_bytes` attached,
    returns `{"documents": [...updated list...]}` to be merged by LangGraph.
    """
    docs: list[dict] = state.get("documents", [])
    if not docs:
        return {}

    # Run all async verifications in a single event-loop call
    try:
        loop = asyncio.get_event_loop()
        updated_docs = loop.run_until_complete(asyncio.gather(*[_verify_one(d) for d in docs]))
    except RuntimeError:
        # No running event loop (e.g., called from sync test context)
        updated_docs = asyncio.run(asyncio.gather(*[_verify_one(d) for d in docs]))

    logger.info(
        "Document node verified %d document(s). Statuses: %s",
        len(updated_docs),
        [d.get("status") for d in updated_docs],
    )

    return {"documents": list(updated_docs)}
