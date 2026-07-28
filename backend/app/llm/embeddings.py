"""Gemini embeddings (free) with a local fallback.

Primary path: Gemini ``gemini-embedding-001`` requested at 768 dims
(``text-embedding-004`` was retired by Google).
Fallback path: ``sentence-transformers`` running locally so the demo never blocks
on quota / missing API key. The local model's native dimension is normalised to
``DIM`` (768) by deterministic padding/truncation, so the pgvector column always
receives consistently sized vectors regardless of which path produced them.

All heavy imports are lazy so importing this module stays cheap.
"""
from __future__ import annotations

from app.config import settings

DIM = 768
MODEL = "models/gemini-embedding-001"
FALLBACK_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_fallback_model = None  # cached SentenceTransformer instance


def _fit_dim(vec: list[float]) -> list[float]:
    """Normalise any vector to exactly DIM dims (truncate or zero-pad)."""
    if len(vec) >= DIM:
        return list(vec[:DIM])
    return list(vec) + [0.0] * (DIM - len(vec))


def _embed_gemini(texts: list[str]) -> list[list[float]]:
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    out: list[list[float]] = []
    for t in texts:
        resp = genai.embed_content(model=MODEL, content=t, output_dimensionality=DIM)
        out.append(_fit_dim(resp["embedding"]))
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


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts to 768-dim vectors.

    Tries Gemini first (when an API key is configured); on any failure or when no
    key is set, falls back to the local sentence-transformers model so ingestion
    and retrieval keep working offline.
    """
    if not texts:
        return []
    if settings.gemini_api_key:
        try:
            return _embed_gemini(texts)
        except Exception as exc:  # noqa: BLE001 — fall back rather than crash the demo
            print(f"[embeddings] Gemini failed ({exc!r}); using local fallback.")
    return _embed_local(texts)


def embed_query(text: str) -> list[float]:
    """Convenience: embed a single query string."""
    return embed([text])[0]
