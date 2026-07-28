"""Gemini embeddings (free) with a local fallback.

Primary path: Gemini ``gemini-embedding-001`` requested at 768 dims
(``text-embedding-004`` was retired by Google).
Fallback path: ``sentence-transformers`` running locally so the demo never blocks
on quota / missing API key. The local model's native dimension is normalised to
``DIM`` (768) by deterministic padding/truncation, so the pgvector column always
receives consistently sized vectors regardless of which path produced them.

IMPORTANT — same size, different space. Zero-padding MiniLM's 384 dims up to 768
makes the vectors *storable* in one column but NOT comparable: a corpus embedded
with Gemini and queried with the fallback (or vice versa) ranks by noise. That is
why every embedding call also reports its model id, which ingestion stamps onto
each chunk and the retriever filters on. Callers that don't care can keep using
``embed`` / ``embed_query``.

All heavy imports are lazy so importing this module stays cheap.
"""
from __future__ import annotations

from app.config import settings

DIM = 768
MODEL = "models/gemini-embedding-001"
FALLBACK_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Model ids stamped onto every chunk. Include the dimensional treatment: two
# corpora built by the same model but padded differently are still incomparable.
GEMINI_MODEL_ID = "gemini-embedding-001@768"
LOCAL_MODEL_ID = "all-MiniLM-L6-v2@384pad768"

# Relevance floors, per model — these are NOT interchangeable.
# Measured against the seeded gov corpus:
#   Gemini : genuine matches 0.60-0.77, unrelated documents 0.43-0.46
#   MiniLM : genuine matches 0.38-0.45 (the 384->768 zero-padding compresses the
#            range, so a Gemini-tuned floor would reject everything)
# A single global threshold cannot serve both. Override with RAG_MIN_SCORE when
# tuning against your own corpus via GET /admin/search.
DEFAULT_MIN_SCORE: dict[str, float] = {
    GEMINI_MODEL_ID: 0.55,
    LOCAL_MODEL_ID: 0.30,
}
FALLBACK_MIN_SCORE = 0.35  # unknown/legacy model id


def default_min_score(model_id: str) -> float:
    return DEFAULT_MIN_SCORE.get(model_id, FALLBACK_MIN_SCORE)

GEMINI_BATCH = 100  # Gemini accepts a list; batching avoids one HTTP call per chunk

_fallback_model = None  # cached SentenceTransformer instance


def _fit_dim(vec: list[float]) -> list[float]:
    """Normalise any vector to exactly DIM dims (truncate or zero-pad)."""
    if len(vec) >= DIM:
        return list(vec[:DIM])
    return list(vec) + [0.0] * (DIM - len(vec))


def _l2_normalise(vec: list[float]) -> list[float]:
    """Scale to unit length.

    Cosine distance is scale-invariant so this does not change ranking, but it
    puts Gemini's ``1 - distance`` score on the same footing as the already
    normalised local path — which is what a shared RAG_MIN_SCORE threshold needs.
    """
    norm = sum(x * x for x in vec) ** 0.5
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def _embed_gemini(texts: list[str]) -> list[list[float]]:
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    out: list[list[float]] = []
    for i in range(0, len(texts), GEMINI_BATCH):
        batch = texts[i : i + GEMINI_BATCH]
        resp = genai.embed_content(model=MODEL, content=batch, output_dimensionality=DIM)
        vectors = resp["embedding"]
        # A single-item request can come back as a bare vector rather than a list
        # of vectors; normalise the shape before zipping.
        if vectors and not isinstance(vectors[0], (list, tuple)):
            vectors = [vectors]
        out.extend(_l2_normalise(_fit_dim(list(v))) for v in vectors)
    return out


def _get_fallback_model():
    global _fallback_model
    if _fallback_model is None:
        from sentence_transformers import SentenceTransformer

        _fallback_model = SentenceTransformer(FALLBACK_MODEL)
    return _fallback_model


def _embed_local(texts: list[str]) -> list[list[float]]:
    model = _get_fallback_model()
    vecs = model.encode(list(texts), convert_to_numpy=True, normalize_embeddings=True)
    return [_fit_dim([float(x) for x in v]) for v in vecs]


def active_model_id() -> str:
    """Which model WOULD run right now, without making a call.

    Best-effort: an actual embed can still fall back to local if Gemini errors,
    which is why ``embed_with_model`` reports what really ran.
    """
    return GEMINI_MODEL_ID if settings.gemini_api_key else LOCAL_MODEL_ID


def embed_with_model(texts: list[str]) -> tuple[list[list[float]], str]:
    """Embed a batch and report which model actually produced the vectors."""
    if not texts:
        return [], active_model_id()
    if settings.gemini_api_key:
        try:
            return _embed_gemini(texts), GEMINI_MODEL_ID
        except Exception as exc:  # noqa: BLE001 — fall back rather than crash the demo
            print(f"[embeddings] Gemini failed ({exc!r}); using local fallback.")
    return _embed_local(texts), LOCAL_MODEL_ID


def embed_query_with_model(text: str) -> tuple[list[float], str]:
    """Embed a single query and report the model that produced it."""
    vectors, model_id = embed_with_model([text])
    return vectors[0], model_id


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts to 768-dim vectors (model id discarded)."""
    return embed_with_model(texts)[0]


def embed_query(text: str) -> list[float]:
    """Convenience: embed a single query string."""
    return embed_query_with_model(text)[0]
