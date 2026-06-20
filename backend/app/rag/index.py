"""Owner: M3. Vector index over doc_chunks (pgvector).

The hybrid-RAG embedding side. ``doc_chunks`` is populated by ``app.rag.ingest``
(chunk -> embed -> store with source_url) and queried by ``app.rag.retriever``.

We keep the index thin and own the embedding/search path directly against the
shared ``doc_chunks`` table (M1 schema) rather than letting LlamaIndex manage a
parallel store, so there is a single source of truth and consistent 768-dim
vectors. This module exposes small helpers other M3 code builds on; LlamaIndex's
``PGVectorStore`` can be layered on later without changing the table.
"""
from __future__ import annotations

from sqlalchemy import func, select

from app.db.models import DocChunk
from app.db.session import SessionLocal
from app.rag.retriever import search


def chunk_count() -> int:
    """Number of chunks currently in the index (0 if the table/DB is unavailable)."""
    try:
        with SessionLocal() as db:
            return int(db.execute(select(func.count()).select_from(DocChunk)).scalar_one())
    except Exception:  # noqa: BLE001 — health/info helper must not raise
        return 0


def retrieve(query: str, k: int = 4) -> list[dict]:
    """Top-k chunks for a query, each with ``content``, ``source_url``, ``title``,
    ``score``. Thin pass-through to :func:`app.rag.retriever.search`."""
    return search(query, k=k)
