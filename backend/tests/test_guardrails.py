"""Scope guardrail: only Sri Lankan government-service goals reach a case.

The property that matters: an off-topic goal is refused before it ever
becomes a `Case`, and any LLM/config failure degrades to allowing the
request through — the same fail-open posture as every other model call in
this codebase (see test_m8_i18n_understand.py).
"""
from __future__ import annotations

import json

import pytest

from app import guardrails
from app.config import settings
from app.guardrails import check_scope


@pytest.fixture
def no_llm(monkeypatch):
    """Make any model call an error, so the keyword allow-list can be proven offline."""

    def _boom(*_a, **_k):
        raise AssertionError("the model must not be called on this path")

    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(guardrails.groq_client, "chat", _boom)


@pytest.fixture
def fake_llm(monkeypatch):
    """Return a fixed in_scope verdict, recording what was sent."""
    seen: list[str] = []

    def _make(in_scope: bool):
        def _chat(messages, **_kw):
            seen.append(messages[-1]["content"])
            return json.dumps({"in_scope": in_scope})

        monkeypatch.setattr(settings, "groq_api_key", "test-key")
        monkeypatch.setattr(guardrails.groq_client, "chat", _chat)
        return seen

    return _make


# ── keyword allow-list (no model involved) ──────────────────────────────────


@pytest.mark.parametrize(
    "goal",
    [
        "I lost my NIC and need a passport",
        "I want to renew my driving licence",
        "I need a copy of my birth certificate",
        "I am starting a small business",
        "I want to get married",
        "my land deed was destroyed in a flood",
    ],
)
def test_keyword_allow_list_no_model_call(no_llm, goal):
    result = check_scope(goal)
    assert result.in_scope is True


# ── model-backed classification ─────────────────────────────────────────────


def test_llm_allows_government_goal_without_keyword(fake_llm):
    fake_llm(True)
    result = check_scope("I need to obtain a duplicate of my lost identity document")
    assert result.in_scope is True
    assert result.reason is None


def test_llm_refuses_off_topic_goal(fake_llm):
    fake_llm(False)
    result = check_scope("write me a poem about the ocean")
    assert result.in_scope is False
    assert result.reason == "off_topic"


# ── fail-open behaviour ──────────────────────────────────────────────────────


def test_no_groq_key_allows_by_default(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", None)
    result = check_scope("write me a poem about the ocean")
    assert result.in_scope is True


def test_model_error_allows_by_default(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")

    def _boom(*_a, **_k):
        raise RuntimeError("groq is down")

    monkeypatch.setattr(guardrails.groq_client, "chat", _boom)
    result = check_scope("write me a poem about the ocean")
    assert result.in_scope is True


def test_malformed_model_response_allows_by_default(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(guardrails.groq_client, "chat", lambda *_a, **_k: "not json")
    result = check_scope("write me a poem about the ocean")
    assert result.in_scope is True
