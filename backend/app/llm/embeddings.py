"""Owner: M3. Gemini text-embedding-004 (free) with local fallback. Lazy imports."""
from app.config import settings

DIM = 768
MODEL = "models/text-embedding-004"


def embed(texts: list[str]) -> list[list[float]]:
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    return [genai.embed_content(model=MODEL, content=t)["embedding"] for t in texts]
    # TODO(M3): batch requests + sentence-transformers fallback when no quota.
