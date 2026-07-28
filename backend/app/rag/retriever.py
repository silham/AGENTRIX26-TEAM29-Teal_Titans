"""Owner: M3. Query -> relevant chunks with source URLs (for citations).

Vector search over the ``doc_chunks`` pgvector column using cosine distance.
Returns the top-k chunks each carrying its ``source_url`` so the Knowledge node
can surface clickable citations, and the Planner can ground custom procedures in
real uploaded documents.

Degradation policy: ``search`` never raises — a missing DB, absent pgvector or
empty corpus yields ``[]`` so the agent graph keeps running. That silence is
deliberate for the graph but useless for an operator, so every failure is logged
and ``health()`` reports the real state to GET /admin/knowledge/stats.
"""
from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.config import settings
from app.db.models import DocChunk
from app.db.session import SessionLocal, engine
from app.llm.embeddings import active_model_id, default_min_score, embed_query_with_model

logger = logging.getLogger(__name__)

_warned_dialect = False
_warned_unstamped = False


def _is_postgres() -> bool:
    return engine.dialect.name == "postgresql"


def search(
    query: str,
    k: int = 4,
    *,
    min_score: float | None = None,
    strict_model: bool = True,
) -> list[dict]:
    """Return up to ``k`` chunks most similar to ``query``.

    Each result: ``{content, source_url, title, document_id, chunk_index, score}``
    where ``score`` is a similarity in [0, 1] (higher is closer).

    ``strict_model`` restricts results to chunks embedded by the same model as the
    query. Vectors from different models are not comparable (see embeddings.py),
    so mixing them ranks by noise; excluding is better than misleading.
    """
    global _warned_dialect, _warned_unstamped

    query = (query or "").strip()
    if not query:
        return []

    if not _is_postgres():
        # Vector(768).with_variant(Text, "sqlite") means cosine_distance emits
        # invalid SQL here. Short-circuit loudly instead of letting the exception
        # be caught below and look like "the corpus is empty".
        if not _warned_dialect:
            _warned_dialect = True
            logger.warning(
                "Vector search unavailable on the '%s' dialect — RAG retrieval is disabled. "
                "Set DATABASE_URL to a Postgres+pgvector instance to enable it.",
                engine.dialect.name,
            )
        return []

    try:
        vector, query_model = embed_query_with_model(query)
    except Exception:  # noqa: BLE001 — never break the graph on embedding errors
        logger.warning("Embedding the query failed; returning no passages.", exc_info=True)
        return []

    # Explicit argument wins, then the RAG_MIN_SCORE override, then the floor
    # tuned for whichever model actually embedded the query.
    if min_score is not None:
        threshold = min_score
    elif settings.rag_min_score is not None:
        threshold = settings.rag_min_score
    else:
        threshold = default_min_score(query_model)

    try:
        with SessionLocal() as db:
            # cosine_distance in [0, 2]; similarity = 1 - distance.
            distance = DocChunk.embedding.cosine_distance(vector).label("distance")
            stmt = (
                select(
                    DocChunk.content,
                    DocChunk.source_url,
                    DocChunk.title,
                    DocChunk.document_id,
                    DocChunk.chunk_index,
                    distance,
                )
                .where(DocChunk.embedding.isnot(None))
                .order_by(distance)
                # Over-fetch: the threshold and the model filter both drop rows,
                # and trimming after them keeps k results available.
                .limit(k * 3)
            )
            if strict_model:
                stmt = stmt.where(DocChunk.embedding_model == query_model)
            rows = db.execute(stmt).all()

            if strict_model and not rows and not _warned_unstamped:
                unstamped = db.execute(
                    select(func.count())
                    .select_from(DocChunk)
                    .where(DocChunk.embedding_model.is_(None))
                ).scalar_one()
                if unstamped:
                    _warned_unstamped = True
                    logger.warning(
                        "%d doc_chunks have no embedding_model and were excluded from search "
                        "(their provenance is unknown). Re-run `python -m app.rag.ingest` or "
                        "reindex from /admin to restamp them.",
                        unstamped,
                    )
    except Exception:  # noqa: BLE001 — DB unavailable -> degrade gracefully
        logger.warning("Vector search failed; returning no passages.", exc_info=True)
        return []

    results = [
        {
            "content": r.content,
            "source_url": r.source_url,
            "title": r.title,
            "document_id": r.document_id,
            "chunk_index": r.chunk_index,
            "score": round(1.0 - float(r.distance), 4),
        }
        for r in rows
    ]
    return [r for r in results if r["score"] >= threshold][:k]


def health() -> dict:
    """Report the real state of the vector store. Never raises.

    Surfaced by GET /admin/knowledge/stats — this is how an operator sees the
    failures that ``search`` deliberately swallows.
    """
    info: dict = {
        "ok": False,
        "dialect": engine.dialect.name,
        "active_model": active_model_id(),
        "chunks": 0,
        "chunks_by_model": {},
        "unstamped_chunks": 0,
        "orphan_chunks": 0,
        "error": None,
    }

    if not _is_postgres():
        info["error"] = (
            f"Vector search requires Postgres + pgvector; DATABASE_URL uses "
            f"'{engine.dialect.name}'. Retrieval is disabled."
        )
        return info

    try:
        with SessionLocal() as db:
            info["chunks"] = db.execute(
                select(func.count()).select_from(DocChunk)
            ).scalar_one()
            info["chunks_by_model"] = {
                (model or "unknown"): count
                for model, count in db.execute(
                    select(DocChunk.embedding_model, func.count()).group_by(
                        DocChunk.embedding_model
                    )
                ).all()
            }
            info["unstamped_chunks"] = info["chunks_by_model"].get("unknown", 0)
            info["orphan_chunks"] = db.execute(
                select(func.count())
                .select_from(DocChunk)
                .where(DocChunk.document_id.is_(None))
            ).scalar_one()
        info["ok"] = True
    except Exception as exc:  # noqa: BLE001 — health must report, not raise
        logger.warning("Retriever health check failed.", exc_info=True)
        info["error"] = f"{type(exc).__name__}: {exc}"

    return info
