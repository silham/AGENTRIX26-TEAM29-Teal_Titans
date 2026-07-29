"""Owner: M6. Wire formats for the admin knowledge-base API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KnowledgeDocumentOut(BaseModel):
    """A document in the knowledge base, as shown in the admin table."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    title: str | None = None
    source_url: str | None = None
    mime: str | None = None
    size_bytes: int = 0
    page_count: int | None = None
    char_count: int = 0
    chunk_count: int = 0
    extraction_method: str | None = None
    embedding_model: str | None = None
    status: str
    error: str | None = None
    uploaded_by: str
    uploaded_at: datetime
    updated_at: datetime


class KnowledgeListResponse(BaseModel):
    documents: list[KnowledgeDocumentOut]
    total: int


class KnowledgeStats(BaseModel):
    documents: int
    documents_by_status: dict[str, int]
    chunks: int
    # retriever.health() — dialect, per-model chunk counts, orphans, error.
    # This is where failures the graph swallows become visible to an operator.
    retrieval: dict


class KnowledgeDeleteResponse(BaseModel):
    id: str
    deleted: bool
    chunks_removed: int


class KnowledgeSearchHit(BaseModel):
    title: str | None = None
    source_url: str | None = None
    document_id: str | None = None
    chunk_index: int = 0
    score: float
    snippet: str


class KnowledgeSearchResponse(BaseModel):
    query: str
    model: str
    min_score: float
    hits: list[KnowledgeSearchHit]
