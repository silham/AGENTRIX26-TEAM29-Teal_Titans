"""Owner: M5. Document persistence — create, read, update status, delete."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document


def list_documents(db: Session, *, case_id: UUID) -> list[Document]:
    """Return all documents belonging to a case."""
    return list(db.scalars(select(Document).where(Document.case_id == case_id)))


def get_document(db: Session, *, document_id: UUID) -> Document | None:
    """Fetch a single document by id."""
    return db.get(Document, document_id)


def create_document(
    db: Session,
    *,
    case_id: UUID,
    name: str,
    doc_type: str | None = None,
    storage_path: str | None = None,
    status: str = "missing",
    issues: list[str] | None = None,
) -> Document:
    """Persist a new Document row and return it."""
    doc = Document(
        id=uuid.uuid4(),
        case_id=case_id,
        name=name,
        type=doc_type,
        storage_path=storage_path,
        status=status,
        issues=issues or [],
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def update_status(
    db: Session,
    *,
    document_id: UUID,
    status: str,
    doc_type: str | None = None,
    issues: list[str] | None = None,
    storage_path: str | None = None,
) -> Document | None:
    """Update verification result fields on an existing document row."""
    doc = db.get(Document, document_id)
    if doc is None:
        return None
    doc.status = status
    if doc_type is not None:
        doc.type = doc_type
    if issues is not None:
        doc.issues = issues
    if storage_path is not None:
        doc.storage_path = storage_path
    db.commit()
    db.refresh(doc)
    return doc


def delete_document(db: Session, *, document_id: UUID, user_id: str) -> bool:
    """
    Delete a document row ONLY if the owning case belongs to user_id.
    Returns True on success, False if not found or not owned.
    """
    doc = db.get(Document, document_id)
    if doc is None:
        return False
    # Ownership check via the parent case
    from app.db.models import Case

    case = db.get(Case, doc.case_id)
    if case is None or case.user_id != user_id:
        return False
    db.delete(doc)
    db.commit()
    return True
