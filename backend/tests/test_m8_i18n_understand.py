"""Input normalisation: mixed script, transliteration, and the English fast path.

The property that matters: whatever a citizen writes, the graph receives
English, and a failure here degrades to today's behaviour rather than a 500.
"""
from __future__ import annotations

import json

import pytest

from app.config import settings
from app.i18n import understand
from app.i18n.understand import detect_script, normalize_input


@pytest.fixture
def no_llm(monkeypatch):
    """Make any model call an error, so the fast path can be proven offline."""

    def _boom(*_a, **_k):
        raise AssertionError("the model must not be called on this path")

    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(understand.groq_client, "chat", _boom)


@pytest.fixture
def fake_llm(monkeypatch):
    """Return a fixed analysis, recording what was sent."""
    seen: list[str] = []

    def _make(language: str, english: str):
        def _chat(messages, **_kw):
            seen.append(messages[-1]["content"])
            return json.dumps({"language": language, "english": english})

        monkeypatch.setattr(settings, "groq_api_key", "test-key")
        monkeypatch.setattr(understand.groq_client, "chat", _chat)
        return seen

    return _make


# ── script detection (no model involved) ────────────────────────────────────


@pytest.mark.parametrize(
    "text,expected",
    [
        ("I lost my NIC", "latin"),
        ("මගේ ජාතික හැඳුනුම්පත නැති වුණා", "sinhala"),
        ("எனது தேசிய அடையாள அட்டை தொலைந்தது", "tamil"),
        ("මට passport එකක් ඕන", "mixed"),
        ("enakku passport venum", "latin"),
    ],
)
def test_detect_script(text, expected):
    assert detect_script(text) == expected


# ── the English fast path ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "goal",
    [
        # The six landing-page shortcuts, verbatim from app/page.tsx.
        "I lost my NIC and need a replacement",
        "I want to apply for a passport",
        "I want to renew my driving licence",
        "I need a copy of my birth certificate",
        "I am starting a small business",
        "I lost all my documents in a flood",
        # The example chips.
        "I lost my NIC and need to apply for a passport",
        "I want to get married",
    ],
)
def test_english_shortcuts_make_no_model_call(no_llm, goal):
    """The most-travelled path in the app must be free and deterministic."""
    result = normalize_input(goal)

    assert result.english == goal
    assert result.detected_language == "en"
    assert result.used_llm is False


def test_transliteration_is_not_mistaken_for_english(fake_llm):
    """Singlish is ASCII, so ASCII alone cannot be the fast-path test."""
    seen = fake_llm("si", "I need a passport")

    result = normalize_input("mata passport ekak ona")

    assert seen, "romanised Sinhala must reach the model"
    assert result.detected_language == "si"
    assert result.english == "I need a passport"


def test_tamil_transliteration_reaches_the_model(fake_llm):
    seen = fake_llm("ta", "I need a passport")

    result = normalize_input("enakku passport venum")

    assert seen
    assert result.detected_language == "ta"


# ── script + mixed input ────────────────────────────────────────────────────


def test_sinhala_script_is_normalised_to_english(fake_llm):
    fake_llm("si", "I lost my NIC")

    result = normalize_input("මගේ ජාතික හැඳුනුම්පත නැති වුණා")

    assert result.english == "I lost my NIC"
    assert result.detected_language == "si"
    assert result.script == "sinhala"
    assert result.used_llm is True


def test_mixed_script_is_normalised(fake_llm):
    fake_llm("si", "I need a passport")

    result = normalize_input("මට passport එකක් ඕන")

    assert result.english == "I need a passport"
    assert result.script == "mixed"


# ── fail-open ───────────────────────────────────────────────────────────────


def test_model_failure_falls_back_to_the_original(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(
        understand.groq_client,
        "chat",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("groq down")),
    )

    result = normalize_input("මට passport එකක් ඕන")

    assert result.english == "මට passport එකක් ඕන"
    assert result.detected_language == "en"
    assert result.used_llm is False


def test_no_api_key_falls_back_without_raising(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "")
    result = normalize_input("මට passport එකක් ඕන")
    assert result.english == "මට passport එකක් ඕන"


def test_unparseable_response_falls_back(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(understand.groq_client, "chat", lambda *a, **k: "not json")

    result = normalize_input("මට passport එකක් ඕන")
    assert result.english == "මට passport එකක් ඕන"


def test_empty_english_in_response_falls_back_to_original(fake_llm):
    fake_llm("si", "")
    result = normalize_input("මට passport එකක් ඕන")
    assert result.english == "මට passport එකක් ඕන"


def test_unsupported_detected_language_is_coerced_to_english(fake_llm):
    """A language we do not support must not end up on the case row.

    `Case.language` is echoed to the client, which switches the UI to it — an
    unsupported code would leave the app with no dictionary to render.
    """
    fake_llm("fr", "I need a passport")

    # Non-ASCII so this reaches the model rather than the English fast path.
    result = normalize_input("මට passport එකක් ඕන")

    assert result.detected_language == "en"
    assert result.english == "I need a passport"
