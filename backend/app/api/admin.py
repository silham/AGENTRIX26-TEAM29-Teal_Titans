"""Owner: M6. Admin-only knowledge-base management.

Government documents uploaded here are extracted, chunked, embedded and indexed
into ``doc_chunks``, which is what the Knowledge and Planner nodes retrieve from
when answering citizen queries.

Every route is gated by ``require_admin`` (ADMIN_EMAILS allowlist + role claim).

Routes:
  POST   /admin/knowledge              upload a document (202; ingestion is async)
  GET    /admin/knowledge              list documents
  GET    /admin/knowledge/stats        counts + retrieval health
  GET    /admin/knowledge/{id}         document detail
  POST   /admin/knowledge/{id}/reindex re-extract and re-embed
  DELETE /admin/knowledge/{id}         remove document, chunks and stored file
  GET    /admin/search                 retrieval smoke test
"""

from __future__ import annotations

import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.auth.jwt import CurrentUser, require_admin
from app.config import settings
from app.db.session import get_db
from app.documents import storage
from app.documents.validation import read_capped, validate_extension
from app.rag import pipeline, retriever
from app.repositories import knowledge as knowledge_repo
from app.schemas.knowledge import (
    KnowledgeDeleteResponse,
    KnowledgeDocumentOut,
    KnowledgeListResponse,
    KnowledgeSearchHit,
    KnowledgeSearchResponse,
    KnowledgeStats,
)

logger = logging.getLogger(__name__)

# The dependency on the router (not per-route) means a new endpoint added here
# cannot accidentally ship ungated.
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)

# Knowledge-base files live outside the per-citizen tree in storage.
_KB_OWNER = "_knowledge"
_KB_BUCKET = "_admin"


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@router.post("/knowledge", response_model=KnowledgeDocumentOut, status_code=202)
async def upload_knowledge(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    source_url: str | None = Form(None),
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> KnowledgeDocumentOut:
    """Accept a government document and queue it for indexing.

    Returns 202 immediately: a scanned 20-page PDF is 20-60s of OCR before
    embedding even starts, and the frontend's fetch wrapper aborts at 15s.
    Poll GET /admin/knowledge for status.
    """
    validate_extension(file.filename)
    data = await read_capped(file)

    try:
        storage_path = await storage.upload_file(
            data,
            file.filename or "upload",
            user_id=_KB_OWNER,
            case_id=_KB_BUCKET,
        )
    except storage.StorageUploadError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    doc = knowledge_repo.create_document(
        db,
        filename=file.filename or "upload",
        uploaded_by=user.email or user.id,
        title=(title or "").strip() or None,
        source_url=(source_url or "").strip() or None,
        storage_path=storage_path,
        mime=file.content_type,
        size_bytes=len(data),
        status="pending",
    )

    background.add_task(pipeline.ingest_uploaded_document, doc.id)
    return KnowledgeDocumentOut.model_validate(doc)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


@router.get("/knowledge", response_model=KnowledgeListResponse)
def list_knowledge(
    status: str | None = Query(None, description="pending | processing | ready | failed"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> KnowledgeListResponse:
    docs = knowledge_repo.list_documents(db, status=status, limit=limit, offset=offset)
    return KnowledgeListResponse(
        documents=[KnowledgeDocumentOut.model_validate(d) for d in docs],
        total=knowledge_repo.stats(db)["documents"],
    )


@router.get("/knowledge/stats", response_model=KnowledgeStats)
def knowledge_stats(db: Session = Depends(get_db)) -> KnowledgeStats:
    """Counts plus the retrieval health the agent graph deliberately swallows."""
    return KnowledgeStats(**knowledge_repo.stats(db), retrieval=retriever.health())


@router.get("/knowledge/{document_id}", response_model=KnowledgeDocumentOut)
def get_knowledge(document_id: str, db: Session = Depends(get_db)) -> KnowledgeDocumentOut:
    doc = knowledge_repo.get_document(db, document_id=document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return KnowledgeDocumentOut.model_validate(doc)


# ---------------------------------------------------------------------------
# Reindex / delete
# ---------------------------------------------------------------------------


@router.post("/knowledge/{document_id}/reindex", response_model=KnowledgeDocumentOut, status_code=202)
def reindex_knowledge(
    document_id: str,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
) -> KnowledgeDocumentOut:
    """Re-extract and re-embed. Use after a failure, or to restamp with a new
    embedding model once GEMINI_API_KEY is configured."""
    doc = knowledge_repo.get_document(db, document_id=document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not doc.storage_path:
        raise HTTPException(
            status_code=409,
            detail="This document has no stored file (it was seeded by the corpus CLI). "
            "Re-run `python -m app.rag.ingest` instead.",
        )

    doc = knowledge_repo.set_status(db, document_id=document_id, status="pending", error=None)
    background.add_task(pipeline.ingest_uploaded_document, document_id)
    return KnowledgeDocumentOut.model_validate(doc)


@router.delete("/knowledge/{document_id}", response_model=KnowledgeDeleteResponse)
async def delete_knowledge(
    document_id: str,
    db: Session = Depends(get_db),
) -> KnowledgeDeleteResponse:
    """Remove the document, its chunks (FK cascade) and its stored file."""
    doc = knowledge_repo.get_document(db, document_id=document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    chunks_removed = doc.chunk_count
    storage_path = doc.storage_path
    knowledge_repo.delete_document(db, document_id=document_id)

    if storage_path:
        try:
            await storage.delete_file(storage_path)
        except Exception as exc:  # noqa: BLE001 — the row is already gone
            logger.warning("Could not delete stored file %s: %s", storage_path, exc)

    return KnowledgeDeleteResponse(id=document_id, deleted=True, chunks_removed=chunks_removed)


# ---------------------------------------------------------------------------
# Retrieval smoke test
# ---------------------------------------------------------------------------


@router.get("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    q: str = Query(..., min_length=2, description="Free-text query"),
    k: int = Query(8, ge=1, le=50),
    min_score: float | None = Query(
        None, description="Override RAG_MIN_SCORE; pass 0 to see everything ranked."
    ),
) -> KnowledgeSearchResponse:
    """Run the same retrieval the agent graph uses, and show the raw scores.

    This is how RAG_MIN_SCORE gets tuned, and how a fresh upload is confirmed
    live without running a whole case.
    """
    from app.llm.embeddings import active_model_id, default_min_score

    model = active_model_id()
    hits = retriever.search(q, k=k, min_score=min_score)
    # Mirror the retriever's precedence so the number shown is the one applied.
    effective = min_score
    if effective is None:
        effective = settings.rag_min_score
    if effective is None:
        effective = default_min_score(model)

    return KnowledgeSearchResponse(
        query=q,
        model=model,
        min_score=effective,
        hits=[
            KnowledgeSearchHit(
                title=h.get("title"),
                source_url=h.get("source_url"),
                document_id=h.get("document_id"),
                chunk_index=h.get("chunk_index") or 0,
                score=h["score"],
                snippet=(h.get("content") or "")[:300],
            )
            for h in hits
        ],
    )
