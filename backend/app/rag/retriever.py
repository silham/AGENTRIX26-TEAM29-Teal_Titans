"""Owner: M3. Query -> relevant chunks with source URLs (for citations).

Vector search over the ``doc_chunks`` pgvector column using cosine distance.
Returns the top-k chunks each carrying its ``source_url`` so the Knowledge node
can surface clickable citations. Falls back to an empty list (never raises) so a
missing DB/corpus degrades gracefully in the demo.
"""
from __future__ import annotations

from sqlalchemy import select

from app.db.models import DocChunk
from app.db.session import SessionLocal
from app.llm.embeddings import embed_query


def search(query: str, k: int = 4) -> list[dict]:
    """Return up to ``k`` chunks most similar to ``query``.

    Each result: ``{content, source_url, title, score}`` where ``score`` is a
    similarity in [0, 1] (higher is closer).
    """
    query = (query or "").strip()
    if not query:
        return []

    try:
        vector = embed_query(query)
    except Exception as exc:  # noqa: BLE001 — never break the graph on embedding errors
        print(f"[retriever] embedding failed ({exc!r}); returning no passages.")
        return []

    try:
        with SessionLocal() as db:
            # cosine_distance in [0, 2]; similarity = 1 - distance.
            distance = DocChunk.embedding.cosine_distance(vector).label("distance")
            rows = db.execute(
                select(
                    DocChunk.content,
                    DocChunk.source_url,
                    DocChunk.title,
                    distance,
                )
                .where(DocChunk.embedding.isnot(None))
                .order_by(distance)
                .limit(k)
            ).all()
    except Exception as exc:  # noqa: BLE001 — DB unavailable -> degrade gracefully
        print(f"[retriever] vector search failed ({exc!r}); returning no passages.")
        return []

    return [
        {
            "content": r.content,
            "source_url": r.source_url,
            "title": r.title,
            "score": round(1.0 - float(r.distance), 4),
        }
        for r in rows
    ]
