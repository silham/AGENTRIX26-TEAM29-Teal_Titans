"""Owner: M6. The single chunk -> embed -> store path for the knowledge base.

Both entry points share it:
  * ``python -m app.rag.ingest``      — seeds data/corpus/*.txt
  * ``POST /admin/knowledge``         — admin uploads (background task)

so a seeded corpus file and an uploaded PDF end up as the same kind of row and
can be listed, reindexed and deleted through the same admin surface.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import DocChunk
from app.db.session import SessionLocal
from app.llm.embeddings import embed_with_model
from app.repositories import knowledge as knowledge_repo

logger = logging.getLogger(__name__)


def _bind_vector(db: Session, vector: list[float]):
    """Adapt a vector to the target column type.

    On Postgres the column is a real pgvector and takes the list directly. On
    SQLite it degrades to Text, where binding a list raises InterfaceError — so
    serialise. Nothing reads it back there (retrieval short-circuits on
    non-Postgres dialects); this just lets ingestion complete on the default
    SQLite dev config instead of crashing.
    """
    if db.bind is not None and db.bind.dialect.name != "postgresql":
        return json.dumps(vector)
    return vector


def store_document_chunks(
    db: Session,
    *,
    document_id: str | None,
    source_url: str | None,
    title: str | None,
    text: str,
) -> tuple[int, str]:
    """Chunk, embed and REPLACE this document's chunks. Returns (count, model_id).

    Idempotent: prior chunks for the document are deleted first, so re-ingesting
    never duplicates. Does not commit — the caller owns the transaction.
    """
    from app.rag.ingest import chunk_text  # local import: ingest imports this module

    if document_id:
        db.execute(delete(DocChunk).where(DocChunk.document_id == document_id))
    if source_url:
        # Also sweep chunks for this source that predate knowledge_documents
        # (document_id IS NULL). Without this, the first ingest after the
        # migration leaves the old unparented copies behind as duplicates that
        # nothing can subsequently delete or reindex.
        db.execute(
            delete(DocChunk).where(
                DocChunk.source_url == source_url,
                DocChunk.document_id.is_(None),
            )
        )

    chunks = chunk_text(text)
    if not chunks:
        return 0, ""

    vectors, model_id = embed_with_model(chunks)
    for index, (content, vector) in enumerate(zip(chunks, vectors, strict=True)):
        db.add(
            DocChunk(
                document_id=document_id,
                chunk_index=index,
                source_url=source_url,
                title=title,
                content=content,
                embedding=_bind_vector(db, vector),
                embedding_model=model_id,
            )
        )
    return len(chunks), model_id


def ingest_uploaded_document(document_id: str) -> None:
    """Background worker: stored file -> extract -> chunk -> embed -> store.

    Runs as a Starlette BackgroundTask. Deliberately a plain ``def``: Starlette
    runs sync background tasks in a threadpool, so the blocking OCR and HTTP
    calls inside cannot stall the event loop and freeze concurrent SSE runs.

    Opens its own session — the request's ``get_db`` session is already closed by
    the time this runs. Never raises: a background task that throws would surface
    as an unhandled error with no trace back to the document.
    """
    from app.documents import storage
    from app.rag import extract

    try:
        with SessionLocal() as db:
            if not knowledge_repo.claim_for_processing(db, document_id=document_id):
                logger.info("Document %s is not pending; skipping ingestion.", document_id)
                return

            doc = knowledge_repo.get_document(db, document_id=document_id)
            if doc is None:
                logger.warning("Document %s vanished before ingestion.", document_id)
                return

            filename = doc.filename
            mime = doc.mime
            source_url = doc.source_url
            title = doc.title
            storage_path = doc.storage_path

        if not storage_path:
            raise RuntimeError("Document has no stored file to read.")

        data = storage.read_file(storage_path)
        extracted = extract.extract(data, filename, mime)

        with SessionLocal() as db:
            count, model_id = store_document_chunks(
                db,
                document_id=document_id,
                source_url=source_url,
                title=title,
                text=extracted.text,
            )
            db.commit()
            knowledge_repo.set_status(
                db,
                document_id=document_id,
                status="ready",
                error=None,
                chunk_count=count,
                char_count=len(extracted.text),
                page_count=extracted.page_count,
                extraction_method=extracted.method,
                embedding_model=model_id,
            )
        logger.info("Ingested %s: %d chunk(s) via %s.", filename, count, extracted.method)

    except Exception as exc:  # noqa: BLE001 — must never escape into Starlette
        logger.error("Ingestion failed for document %s.", document_id, exc_info=True)
        try:
            with SessionLocal() as db:
                knowledge_repo.set_status(
                    db,
                    document_id=document_id,
                    status="failed",
                    error=str(exc)[:2000],
                    chunk_count=0,
                )
        except Exception:  # noqa: BLE001 — nothing left to do but log
            logger.error("Could not record the failure for %s.", document_id, exc_info=True)
