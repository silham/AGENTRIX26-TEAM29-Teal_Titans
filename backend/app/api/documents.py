"""Owner: M5. Document upload / verify / delete API endpoints.

Routes (all protected by M1's get_current_user):
  POST   /documents            upload + verify a document
  GET    /documents/{id}       fetch document metadata + signed URL
  DELETE /documents/{id}       citizen data erasure (ownership-checked)
  GET    /documents/_ping      health probe
"""

from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.jwt import CurrentUser, get_current_user
from app.db.session import get_db
from app.documents import storage
from app.llm.gemini_vision import GeminiQuotaExceeded, GeminiVisionError, analyze_document
from app.repositories import documents as doc_repo
from app.schemas.document import (
    DocumentDeleteResponse,
    DocumentGetResponse,
    DocumentStatus,
    DocumentType,
    DocumentUploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# ---------------------------------------------------------------------------
# Health probe
# ---------------------------------------------------------------------------


@router.get("/_ping")
def ping(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"ok": True, "owner": "M5"}


# ---------------------------------------------------------------------------
# POST /documents — upload + verify
# ---------------------------------------------------------------------------


@router.post("", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    case_id: str = Form(..., description="The citizen case this document belongs to."),
    expected_name: str = Form(..., description="Human label: 'NIC', 'Birth Certificate', etc."),
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    """
    Upload a document image, run Gemini Vision verification (with Tesseract fallback),
    persist the result, and return a verdict with issues list.

    Upserts by (case, name): when the case already has a matching required
    document (usually a 'missing' placeholder from the checklist agent), that
    row is updated instead of creating a duplicate.
    """
    try:
        case_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="case_id is not a valid UUID.")

    # Ownership: the case must belong to the requesting user.
    from app.repositories.cases import get_case
    if get_case(db, case_id=case_uuid, user_id=user.id) is None:
        raise HTTPException(status_code=404, detail="Case not found")

    # Read bytes
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    mime_type = file.content_type or "application/octet-stream"

    # 1. Store the file
    try:
        storage_path = await storage.upload_file(
            image_bytes,
            file.filename or "upload",
            user_id=user.id,
            case_id=case_id,
        )
    except storage.StorageUploadError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # 2. Verify via Gemini Vision (with OCR fallback)
    confidence = 0.0
    detected_type = DocumentType.UNKNOWN
    issues: list[str] = []

    try:
        result = await analyze_document(image_bytes, expected_name=expected_name, mime_type=mime_type)
        detected_type = result.detected_type
        issues = result.issues
        confidence = result.confidence
    except GeminiQuotaExceeded:
        logger.warning("Gemini quota exceeded — falling back to Tesseract for '%s'", expected_name)
        from app.documents.ocr import classify_from_ocr_text
        result = classify_from_ocr_text(image_bytes, expected_name=expected_name)
        detected_type = result.detected_type
        issues = result.issues
        confidence = result.confidence
    except GeminiVisionError as exc:
        logger.error("Gemini Vision error: %s", exc)
        issues = ["Document verification service unavailable. File stored; please retry."]

    # 3. Determine status
    if not issues:
        status = DocumentStatus.ACCEPTED
    elif detected_type == DocumentType.UNKNOWN:
        status = DocumentStatus.REJECTED
    else:
        status = DocumentStatus.INCOMPLETE

    # 4. Persist to DB — update the existing required-document row when present.
    existing = doc_repo.find_by_name(db, case_id=case_uuid, name=expected_name)
    if existing is not None:
        doc = doc_repo.update_status(
            db,
            document_id=existing.id,
            status=status.value,
            issues=issues,
            storage_path=storage_path,
        )
    else:
        doc = doc_repo.create_document(
            db,
            case_id=case_uuid,
            name=expected_name,
            doc_type=detected_type.value,
            storage_path=storage_path,
            status=status.value,
            issues=issues,
        )

    # 5. Generate signed URL for accepted docs
    signed_url: str | None = None
    if status == DocumentStatus.ACCEPTED:
        try:
            signed_url = await storage.get_signed_url(storage_path)
        except Exception:
            signed_url = None

    return DocumentUploadResponse(
        id=str(doc.id),
        case_id=str(doc.case_id),
        name=doc.name,
        detected_type=detected_type,
        status=status,
        issues=issues,
        confidence=confidence,
        signed_url=signed_url,
        uploaded_at=doc.uploaded_at,
    )


# ---------------------------------------------------------------------------
# GET /documents/{id}
# ---------------------------------------------------------------------------


@router.get("/{document_id}", response_model=DocumentGetResponse)
async def get_document(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentGetResponse:
    """Fetch document metadata. Scoped to the owning user via case lookup."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="document_id is not a valid UUID.")

    doc = doc_repo.get_document(db, document_id=doc_uuid)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Ownership: check parent case
    from app.db.models import Case
    case = db.get(Case, doc.case_id)
    if case is None or case.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    signed_url: str | None = None
    if doc.storage_path and doc.status == DocumentStatus.ACCEPTED.value:
        try:
            signed_url = await storage.get_signed_url(doc.storage_path)
        except Exception:
            signed_url = None

    return DocumentGetResponse(
        id=str(doc.id),
        case_id=str(doc.case_id),
        name=doc.name,
        detected_type=DocumentType(doc.type) if doc.type else DocumentType.UNKNOWN,
        status=DocumentStatus(doc.status),
        issues=doc.issues or [],
        confidence=0.0,  # not persisted in current model
        signed_url=signed_url,
        uploaded_at=doc.uploaded_at,
    )


# ---------------------------------------------------------------------------
# DELETE /documents/{id}
# ---------------------------------------------------------------------------


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDeleteResponse:
    """
    Permanently delete a document and its stored file.
    Verifies that the requesting user owns the parent case before deleting.
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="document_id is not a valid UUID.")

    # Retrieve before delete so we have the storage_path
    doc = doc_repo.get_document(db, document_id=doc_uuid)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    storage_path = doc.storage_path

    deleted = doc_repo.delete_document(db, document_id=doc_uuid, user_id=user.id)
    if not deleted:
        raise HTTPException(status_code=403, detail="Access denied or document not found.")

    # Remove file from storage (best-effort)
    if storage_path:
        try:
            await storage.delete_file(storage_path)
        except Exception as exc:
            logger.warning("Could not delete storage file %s: %s", storage_path, exc)

    return DocumentDeleteResponse(id=document_id, deleted=True)
