"""Owner: M5. Document persistence (with storage integration). TODO(M5)."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document


def list_documents(db: Session, *, case_id: UUID) -> list[Document]:
    return list(db.scalars(select(Document).where(Document.case_id == case_id)))


# TODO(M5): create_document(...), update_status(...), delete_document(...)
