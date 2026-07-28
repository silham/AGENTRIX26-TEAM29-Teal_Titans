"""Translation cache: fail-open, never poison, never overwrite a human edit.

The cache has no TTL, so a bad write is permanent for that prompt version.
Most of these tests are about what must NOT be written.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db.models import Base, Translation
from app.i18n import translator


@pytest.fixture
def db(monkeypatch):
    """In-memory SQLite standing in for the translation cache.

    StaticPool because the translator opens its own SessionLocal for reads and
    writes; without it each would get a separate empty database.
    """
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(translator, "SessionLocal", Session)
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    return Session


def _rows(Session, lang="si"):
    with Session() as s:
        return s.scalars(select(Translation).where(Translation.lang == lang)).all()


def _fake_gemini(monkeypatch, handler):
    """Patch the raw model call. `handler(texts) -> list[str] | Exception`.

    Patched at `_generate` rather than by faking `google.generativeai` in
    sys.modules: `import google.generativeai as genai` binds via the parent
    package attribute, so a sys.modules fake is bypassed as soon as any other
    test in the session imports the real SDK. Patching here also keeps
    `_call_gemini`'s JSON parsing and length validation under test.
    """
    seen: list[list[str]] = []

    def _fake_generate(payload: str, lang: str) -> str:
        texts = json.loads(payload)
        seen.append(texts)
        result = handler(texts)
        if isinstance(result, Exception):
            raise result
        return json.dumps({"translations": result}, ensure_ascii=False)

    monkeypatch.setattr(translator, "_generate", _fake_generate)
    return seen


# ── happy path ──────────────────────────────────────────────────────────────


def test_translates_and_caches(db, monkeypatch):
    _fake_gemini(monkeypatch, lambda ts: [f"SI:{t}" for t in ts])

    out = translator.translate_many(["Passport", "Birth Certificate"], "si")

    assert out == {"Passport": "SI:Passport", "Birth Certificate": "SI:Birth Certificate"}
    assert len(_rows(db)) == 2
    assert all(r.source == "machine" for r in _rows(db))


def test_partial_cache_hit_only_calls_llm_for_misses(db, monkeypatch):
    _fake_gemini(monkeypatch, lambda ts: [f"SI:{t}" for t in ts])
    translator.translate_many(["A cached one"], "si")

    seen = _fake_gemini(monkeypatch, lambda ts: [f"SI:{t}" for t in ts])
    out = translator.translate_many(["A cached one", "A fresh one"], "si")

    assert seen == [["A fresh one"]], "cached strings must not be re-sent"
    assert out["A cached one"] == "SI:A cached one"


def test_dedupes_identical_strings(db, monkeypatch):
    seen = _fake_gemini(monkeypatch, lambda ts: [f"SI:{t}" for t in ts])

    translator.translate_many(["Same", "Same", "Other"], "si")

    assert seen == [["Same", "Other"]]


def test_english_is_a_no_op(db, monkeypatch):
    seen = _fake_gemini(monkeypatch, lambda ts: [f"SI:{t}" for t in ts])
    assert translator.translate_many(["Passport"], "en") == {"Passport": "Passport"}
    assert seen == []


def test_unsupported_language_falls_back_to_originals(db, monkeypatch):
    seen = _fake_gemini(monkeypatch, lambda ts: [f"X:{t}" for t in ts])
    assert translator.translate_many(["Passport"], "fr") == {"Passport": "Passport"}
    assert seen == []


# ── what must NOT be translated or cached ───────────────────────────────────


@pytest.mark.parametrize("junk", ["", "   ", "12345", "https://gov.lk/a", "—", "%"])
def test_non_text_is_passed_through_untouched(db, monkeypatch, junk):
    seen = _fake_gemini(monkeypatch, lambda ts: [f"SI:{t}" for t in ts])

    assert translator.translate_many([junk], "si") == {junk: junk}
    assert seen == [], "numbers, URLs and punctuation must not reach the model"


def test_model_failure_returns_originals_and_writes_nothing(db, monkeypatch):
    _fake_gemini(monkeypatch, lambda ts: RuntimeError("gemini down"))

    out = translator.translate_many(["Passport", "NIC card"], "si")

    assert out == {"Passport": "Passport", "NIC card": "NIC card"}
    assert _rows(db) == [], "a failed call must not poison the cache"


def test_truncated_response_discards_the_whole_batch(db, monkeypatch):
    """A short array means the model dropped or merged an element.

    Which one is unknowable, so caching any of it would silently mislabel UI
    permanently. The batch fails open instead.
    """
    _fake_gemini(monkeypatch, lambda ts: [f"SI:{t}" for t in ts[:-1]])

    out = translator.translate_many(["One", "Two", "Three"], "si")

    assert out == {"One": "One", "Two": "Two", "Three": "Three"}
    assert _rows(db) == []


def test_empty_element_discards_the_whole_batch(db, monkeypatch):
    _fake_gemini(monkeypatch, lambda ts: [f"SI:{ts[0]}", "   "])

    out = translator.translate_many(["One", "Two"], "si")

    assert out == {"One": "One", "Two": "Two"}
    assert _rows(db) == []


def test_missing_api_key_returns_originals(db, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    seen = _fake_gemini(monkeypatch, lambda ts: [f"SI:{t}" for t in ts])

    assert translator.translate_many(["Passport"], "si") == {"Passport": "Passport"}
    assert seen == []


# ── cache-only mode (the list endpoint) ─────────────────────────────────────


def test_cache_only_never_calls_the_model(db, monkeypatch):
    seen = _fake_gemini(monkeypatch, lambda ts: [f"SI:{t}" for t in ts])

    out = translator.translate_many(["Uncached"], "si", cache_only=True)

    assert seen == [], "the dashboard must never wait on the model"
    assert out == {"Uncached": "Uncached"}


def test_cache_only_still_serves_cached_rows(db, monkeypatch):
    _fake_gemini(monkeypatch, lambda ts: [f"SI:{t}" for t in ts])
    translator.translate_many(["Warm"], "si")

    seen = _fake_gemini(monkeypatch, lambda ts: [f"SI:{t}" for t in ts])
    out = translator.translate_many(["Warm", "Cold"], "si", cache_only=True)

    assert seen == []
    assert out == {"Warm": "SI:Warm", "Cold": "Cold"}


# ── concurrency + human review ──────────────────────────────────────────────


def test_duplicate_insert_does_not_raise(db, monkeypatch):
    """Two concurrent requests for a cold language both miss and both insert."""
    _fake_gemini(monkeypatch, lambda ts: [f"SI:{t}" for t in ts])
    translator.translate_many(["Passport"], "si")

    pairs = {"Passport": "SI:Passport-again"}
    translator._write_cache(pairs, "si")  # must not raise

    rows = _rows(db)
    assert len(rows) == 1
    assert rows[0].translated_text == "SI:Passport", "first write wins"


def test_human_reviewed_row_is_never_overwritten(db, monkeypatch):
    with db() as s:
        s.add(
            Translation(
                source_hash=translator._hash("Divisional Secretariat"),
                lang="si",
                prompt_version=translator.PROMPT_VERSION,
                source_text="Divisional Secretariat",
                translated_text="ප්‍රාදේශීය ලේකම් කාර්යාලය",
                source="human",
            )
        )
        s.commit()

    seen = _fake_gemini(monkeypatch, lambda ts: [f"WRONG:{t}" for t in ts])
    out = translator.translate_many(["Divisional Secretariat"], "si")

    assert out["Divisional Secretariat"] == "ප්‍රාදේශීය ලේකම් කාර්යාලය"
    assert seen == [], "a reviewed row is a cache hit, not a miss"
    assert _rows(db)[0].source == "human"


def test_prompt_version_bump_supersedes_machine_rows(db, monkeypatch):
    """Without a version in the key, a bad translation would be permanent."""
    _fake_gemini(monkeypatch, lambda ts: [f"OLD:{t}" for t in ts])
    translator.translate_many(["Passport"], "si")

    monkeypatch.setattr(translator, "PROMPT_VERSION", translator.PROMPT_VERSION + 1)
    _fake_gemini(monkeypatch, lambda ts: [f"NEW:{t}" for t in ts])

    assert translator.translate_many(["Passport"], "si")["Passport"] == "NEW:Passport"


def test_batches_are_chunked(db, monkeypatch):
    monkeypatch.setattr(translator, "BATCH_SIZE", 3)
    seen = _fake_gemini(monkeypatch, lambda ts: [f"SI:{t}" for t in ts])

    texts = [f"String number {i}" for i in range(7)]
    out = translator.translate_many(texts, "si")

    assert [len(b) for b in seen] == [3, 3, 1]
    assert out["String number 6"] == "SI:String number 6"


def test_one_failed_chunk_does_not_lose_the_others(db, monkeypatch):
    monkeypatch.setattr(translator, "BATCH_SIZE", 2)

    def handler(texts):
        if "String number 2" in texts:
            raise RuntimeError("boom")
        return [f"SI:{t}" for t in texts]

    _fake_gemini(monkeypatch, handler)
    out = translator.translate_many([f"String number {i}" for i in range(4)], "si")

    assert out["String number 0"] == "SI:String number 0"
    assert out["String number 2"] == "String number 2"  # failed chunk, English
    assert len(_rows(db)) == 2
