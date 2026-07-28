"""Cached English → Sinhala/Tamil translation.

Sync on purpose. Callers on the async path must wrap in `asyncio.to_thread`
rather than this module pretending to be async — the Gemini SDK's
`generate_content` is blocking, and an `async def` around a blocking call
stalls the whole event loop while looking correct.

Design constraints worth knowing before editing:

* **Fail open, never fail closed.** Every error path returns the English
  original. A translation outage degrades the app to English; it must never
  turn a working plan into a 500.
* **Never cache an unvalidated batch.** The cache has no TTL, so one bad write
  is permanent for that prompt version. A response that does not line up with
  its input is discarded whole.
* **Cache writes use their own session.** They are not part of the request's
  business transaction, and an IntegrityError on the request session would
  poison the entire response on Postgres.
"""
from __future__ import annotations

import hashlib
import json
import logging

from sqlalchemy import select

from app.config import settings
from app.db.models import Translation
from app.db.session import SessionLocal
from app.i18n.glossary import (
    DEFAULT_LANGUAGE,
    LANGUAGE_NAMES,
    SUPPORTED_LANGUAGES,
    glossary_prompt_block,
)

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"

# Bump when the prompt or glossary changes materially. Part of the cache key,
# so older machine rows are superseded rather than served forever.
PROMPT_VERSION = 1

# Chunk size for one Gemini call. Small enough that a single failure loses
# little and the response stays well inside the output limit; large enough that
# a full case detail is one or two calls.
BATCH_SIZE = 40

# Strings longer than this are almost certainly not UI text (a pasted document,
# a stray blob). Passing them through keeps one bad row from blowing the batch.
MAX_TEXT_LEN = 4000


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _translatable(text: object) -> bool:
    """Whether a value is worth spending a translation call on.

    Numbers, URLs and bare codes round-trip through a model as noise at best
    and corruption at worst, so they are filtered before the request.
    """
    if not isinstance(text, str):
        return False
    stripped = text.strip()
    if not stripped or len(stripped) > MAX_TEXT_LEN:
        return False
    if stripped.startswith(("http://", "https://", "www.")):
        return False
    # No letters at all: digits, punctuation, symbols.
    return any(ch.isalpha() for ch in stripped)


def _system_prompt(lang: str) -> str:
    return (
        f"You translate Sri Lankan government service text from English into "
        f"{LANGUAGE_NAMES.get(lang, lang)}.\n"
        "You will receive a JSON array of strings. Translate each element and "
        "reply ONLY with a JSON object of the form {\"translations\": [...]} "
        "whose array has EXACTLY the same number of elements, in the same "
        "order.\n"
        "Rules:\n"
        "- Write plainly, for an ordinary citizen with no legal training.\n"
        "- Preserve any leading/trailing punctuation, arrows and tick marks.\n"
        "- Never add explanations, notes or extra elements.\n"
        "- Keep numbers, dates, form codes and URLs exactly as they appear.\n"
        + glossary_prompt_block(lang)
    )


def _generate(payload: str, lang: str) -> str:
    """Raw model call. Isolated so tests can exercise parsing without the SDK."""
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(MODEL, system_instruction=_system_prompt(lang))
    response = model.generate_content(
        payload,
        generation_config={
            "temperature": 0.0,
            "response_mime_type": "application/json",
        },
    )
    return response.text


def _call_gemini(texts: list[str], lang: str) -> list[str] | None:
    """One batch → translated strings, or None if anything is off.

    Returning None (rather than partial results) is deliberate: a
    length-mismatched response means the model dropped or merged an element,
    and we cannot tell which. Caching that would silently mislabel UI.
    """
    raw = _generate(json.dumps(texts, ensure_ascii=False), lang)
    payload = json.loads(raw)
    out = payload.get("translations") if isinstance(payload, dict) else payload

    if not isinstance(out, list) or len(out) != len(texts):
        logger.warning(
            "translation batch discarded: expected %d items, got %s",
            len(texts),
            len(out) if isinstance(out, list) else type(out).__name__,
        )
        return None
    if not all(isinstance(item, str) and item.strip() for item in out):
        logger.warning("translation batch discarded: empty or non-string element")
        return None
    return [item.strip() for item in out]


def _read_cache(texts: list[str], lang: str) -> dict[str, str]:
    hashes = {_hash(t): t for t in texts}
    if not hashes:
        return {}
    try:
        with SessionLocal() as db:
            rows = db.execute(
                select(Translation.source_hash, Translation.translated_text).where(
                    Translation.source_hash.in_(list(hashes)),
                    Translation.lang == lang,
                    Translation.prompt_version == PROMPT_VERSION,
                )
            ).all()
        return {hashes[h]: translated for h, translated in rows if h in hashes}
    except Exception:
        logger.warning("translation cache read failed; treating as a miss", exc_info=True)
        return {}


def _write_cache(pairs: dict[str, str], lang: str) -> None:
    """Insert new rows, leaving any existing row (including human edits) alone.

    ON CONFLICT DO NOTHING rather than a read-then-write: two concurrent
    requests for the same cold language both miss and both insert, and the
    plain INSERT would raise on the second.
    """
    if not pairs:
        return
    try:
        with SessionLocal() as db:
            dialect = db.get_bind().dialect.name
            if dialect == "postgresql":
                from sqlalchemy.dialects.postgresql import insert
            elif dialect == "sqlite":
                from sqlalchemy.dialects.sqlite import insert
            else:  # pragma: no cover - no other dialect is used
                logger.warning("no upsert for dialect %s; skipping cache write", dialect)
                return

            stmt = insert(Translation).values(
                [
                    {
                        "source_hash": _hash(src),
                        "lang": lang,
                        "prompt_version": PROMPT_VERSION,
                        "source_text": src,
                        "translated_text": translated,
                        "source": "machine",
                    }
                    for src, translated in pairs.items()
                ]
            )
            db.execute(
                stmt.on_conflict_do_nothing(
                    index_elements=["source_hash", "lang", "prompt_version"]
                )
            )
            db.commit()
    except Exception:
        # A cache write failure costs tokens next time, nothing more.
        logger.warning("translation cache write failed", exc_info=True)


def translate_many(
    texts: list[str], lang: str, *, cache_only: bool = False
) -> dict[str, str]:
    """Map each input string to its translation.

    Always returns an entry for every input: untranslatable, uncached (in
    ``cache_only``) and failed strings map to themselves, so callers can
    substitute unconditionally without None checks.

    ``cache_only=True`` never calls the model. Used by the case-list endpoint,
    where a cold-cache model call would exceed the client's request timeout and
    surface to the citizen as a server error.
    """
    if lang == DEFAULT_LANGUAGE or lang not in SUPPORTED_LANGUAGES:
        return {t: t for t in texts}

    # Dedupe before anything else: requirement names and lock reasons repeat
    # heavily across the steps of one case.
    unique = list(dict.fromkeys(t for t in texts if _translatable(t)))
    result: dict[str, str] = {t: t for t in texts}

    if not unique:
        return result

    cached = _read_cache(unique, lang)
    result.update(cached)

    missing = [t for t in unique if t not in cached]
    if not missing or cache_only or not settings.gemini_api_key:
        if missing and not cache_only and not settings.gemini_api_key:
            logger.debug("no gemini key; %d strings served untranslated", len(missing))
        return result

    for start in range(0, len(missing), BATCH_SIZE):
        batch = missing[start : start + BATCH_SIZE]
        try:
            translated = _call_gemini(batch, lang)
        except Exception:
            logger.warning("translation call failed for %d strings", len(batch), exc_info=True)
            continue
        if translated is None:
            continue
        pairs = dict(zip(batch, translated))
        result.update(pairs)
        _write_cache(pairs, lang)

    return result


def translate_one(text: str, lang: str, *, cache_only: bool = False) -> str:
    return translate_many([text], lang, cache_only=cache_only).get(text, text)
