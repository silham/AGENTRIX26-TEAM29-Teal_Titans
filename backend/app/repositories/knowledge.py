"""Owner: M6. KnowledgeDocument persistence for the admin knowledge base.

IDs are stored as str (models use String(36) columns — passing UUID objects makes
psycopg bind a uuid type against varchar and fail), matching the convention in
repositories/documents.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import DocChunk, KnowledgeDocument


def create_document(
    db: Session,
    *,
    filename: str,
    uploaded_by: str,
    title: str | None = None,
    source_url: str | None = None,
    storage_path: str | None = None,
    mime: str | None = None,
    size_bytes: int = 0,
    status: str = "pending",
) -> KnowledgeDocument:
    """Persist a new knowledge document row and return it."""
    doc = KnowledgeDocument(
        id=str(uuid.uuid4()),
        filename=filename,
        title=title or filename,
        source_url=source_url,
        storage_path=storage_path,
        mime=mime,
        size_bytes=size_bytes,
        uploaded_by=uploaded_by,
        status=status,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_document(db: Session, *, document_id: UUID | str) -> KnowledgeDocument | None:
    return db.get(KnowledgeDocument, str(document_id))


def find_by_filename(db: Session, *, filename: str) -> KnowledgeDocument | None:
    """Look up by filename — how the corpus CLI keeps re-ingestion idempotent."""
    return db.scalars(
        select(KnowledgeDocument).where(KnowledgeDocument.filename == filename).limit(1)
    ).first()


def list_documents(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[KnowledgeDocument]:
    """Newest first, optionally filtered by status."""
    stmt = select(KnowledgeDocument).order_by(KnowledgeDocument.uploaded_at.desc())
    if status:
        stmt = stmt.where(KnowledgeDocument.status == status)
    return list(db.scalars(stmt.limit(limit).offset(offset)))


def set_status(
    db: Session,
    *,
    document_id: UUID | str,
    status: str,
    error: str | None = None,
    **fields,
) -> KnowledgeDocument | None:
    """Update status (and any other column) on a knowledge document."""
    doc = db.get(KnowledgeDocument, str(document_id))
    if doc is None:
        return None
    doc.status = status
    doc.error = error
    for key, value in fields.items():
        setattr(doc, key, value)
    db.commit()
    db.refresh(doc)
    return doc


def claim_for_processing(db: Session, *, document_id: UUID | str) -> bool:
    """Atomically move pending|failed -> processing. False if already claimed.

    The status predicate is the guard against a double-submitted reindex running
    two ingestions over the same document concurrently.
    """
    result = db.execute(
        KnowledgeDocument.__table__.update()
        .where(
            KnowledgeDocument.id == str(document_id),
            KnowledgeDocument.status.in_(["pending", "failed"]),
        )
        .values(status="processing", error=None)
    )
    db.commit()
    return result.rowcount > 0


def delete_document(db: Session, *, document_id: UUID | str) -> KnowledgeDocument | None:
    """Delete the row (chunks cascade). Returns the deleted row, or None."""
    doc = db.get(KnowledgeDocument, str(document_id))
    if doc is None:
        return None
    db.delete(doc)
    db.commit()
    return doc


def chunk_count(db: Session) -> int:
    """Total chunks currently indexed."""
    return db.execute(select(func.count()).select_from(DocChunk)).scalar_one()


def stats(db: Session) -> dict:
    """Document counts by status plus total chunks, for GET /admin/knowledge/stats."""
    by_status = {
        status: count
        for status, count in db.execute(
            select(KnowledgeDocument.status, func.count()).group_by(KnowledgeDocument.status)
        ).all()
    }
    return {
        "documents": sum(by_status.values()),
        "documents_by_status": by_status,
        "chunks": chunk_count(db),
    }


def fail_stale_processing(db: Session, *, older_than_minutes: int = 15) -> int:
    """Mark long-stuck 'processing' rows as failed. Returns how many were reset.

    BackgroundTasks die with the process, so a restart mid-ingestion leaves rows
    stranded in 'processing' forever. Called on app startup.
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=older_than_minutes)
    result = db.execute(
        KnowledgeDocument.__table__.update()
        .where(
            KnowledgeDocument.status == "processing",
            KnowledgeDocument.updated_at < cutoff,
        )
        .values(
            status="failed",
            error="Ingestion was interrupted by a server restart. Use Reindex to retry.",
        )
    )
    db.commit()
    return result.rowcount
