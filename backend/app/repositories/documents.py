"""Owner: M5. Document persistence — create, read, update status, delete."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document


def norm_key(value: str | None) -> str:
    """Canonical spelling of a requirement key.

    One definition shared by ``Document.type``, ``Step.fulfills`` and
    ``Case.parent_requirement_key`` — these three must agree for "I have it" to
    find its step and for a sub-goal to find its requirement. Previously each
    caller rolled its own normaliser, which is how keys drift apart.
    """
    return "_".join(str(value or "").strip().lower().split())


def requirement_key(doc: Document) -> str:
    """The requirement key a document row represents (type, else its name)."""
    return norm_key(doc.type or doc.name)


def list_documents(db: Session, *, case_id: UUID | str) -> list[Document]:
    """Return all documents belonging to a case."""
    return list(db.scalars(select(Document).where(Document.case_id == str(case_id))))


def get_document(db: Session, *, document_id: UUID | str) -> Document | None:
    """Fetch a single document by id."""
    return db.get(Document, str(document_id))


def find_by_name(db: Session, *, case_id: UUID | str, name: str) -> Document | None:
    """Find a case's document by display name (case-insensitive)."""
    for doc in list_documents(db, case_id=case_id):
        if doc.name.strip().lower() == name.strip().lower():
            return doc
    return None


def create_document(
    db: Session,
    *,
    case_id: UUID | str,
    name: str,
    doc_type: str | None = None,
    storage_path: str | None = None,
    status: str = "missing",
    issues: list[str] | None = None,
) -> Document:
    """Persist a new Document row and return it.

    IDs are stored as str (models use String(36) columns — passing UUID objects
    makes psycopg bind a uuid type against varchar and fail).
    """
    doc = Document(
        id=str(uuid.uuid4()),
        case_id=str(case_id),
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
    document_id: UUID | str,
    status: str,
    doc_type: str | None = None,
    issues: list[str] | None = None,
    storage_path: str | None = None,
) -> Document | None:
    """Update verification result fields on an existing document row."""
    doc = db.get(Document, str(document_id))
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


def delete_document(db: Session, *, document_id: UUID | str, user_id: str) -> bool:
    """
    Delete a document row ONLY if the owning case belongs to user_id.
    Returns True on success, False if not found or not owned.
    """
    doc = db.get(Document, str(document_id))
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
