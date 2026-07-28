"""Owner: M6. The anti-hallucination guarantee on custom-procedure plans.

When a goal matches no procedure JSON, the planner asks Groq for a plan. With
knowledge-base passages available it must ground that plan in them — and, more
importantly, any source_url the model did NOT copy from a passage must be
stripped in Python. The prompt asks for this; the prompt is not the guarantee.
"""
import json

import pytest

from app.config import settings
from app.graph.nodes import planner as planner_mod
from app.rag import retriever

REAL_URL = "https://pensions.gov.lk/wop-circular-2024"
FAKE_URL = "https://fake.gov.lk/invented-page"

PASSAGE = {
    "content": "Widows and Orphans Pension applications go to the Department of Pensions.",
    "source_url": REAL_URL,
    "title": "W&OP Circular 2024",
    "document_id": "doc-1",
    "chunk_index": 0,
    "score": 0.82,
}

MODEL_REPLY = json.dumps(
    {
        "service_name": "Widows and Orphans Pension",
        "office": "Department of Pensions",
        "steps": [
            {"title": "Obtain the death certificate", "description": "From the Registrar General.",
             "source_url": REAL_URL, "grounded": True},
            {"title": "Submit the claim form", "description": "At the Department of Pensions.",
             "source_url": FAKE_URL, "grounded": False},
            {"title": "Await assessment", "description": "Processing takes several weeks.",
             "source_url": None, "grounded": False},
        ],
        "requirements": ["Death certificate", "Marriage certificate"],
    }
)


@pytest.fixture
def groq_enabled(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")


@pytest.fixture
def fake_chat(monkeypatch):
    """Capture the messages sent to Groq and reply with MODEL_REPLY."""
    sent: dict = {}

    def _chat(messages, **_kwargs):
        sent["messages"] = messages
        return MODEL_REPLY

    monkeypatch.setattr("app.llm.groq_client.chat", _chat)
    return sent


def _with_passages(monkeypatch, passages):
    monkeypatch.setattr(planner_mod, "_retrieval_context", lambda goal: (
        "\n".join(f"source_url: {p['source_url']}" for p in passages) if passages else "",
        passages,
    ))


def test_fabricated_source_url_is_stripped(monkeypatch, groq_enabled, fake_chat):
    """This is the actual control — the model was told not to invent URLs and
    invented one anyway."""
    _with_passages(monkeypatch, [PASSAGE])
    steps, requirements, passages = planner_mod._generate_custom_plan("widows pension")

    urls = [s["source_url"] for s in steps]
    assert REAL_URL in urls
    assert FAKE_URL not in urls
    assert urls[1] is None  # the fabricated one was nulled, the step survives
    assert requirements == ["Death certificate", "Marriage certificate"]
    assert passages == [PASSAGE]


def test_passages_and_grounding_rules_reach_the_prompt(monkeypatch, groq_enabled, fake_chat):
    _with_passages(monkeypatch, [PASSAGE])
    planner_mod._generate_custom_plan("widows pension")

    system, user = fake_chat["messages"]
    assert "GROUNDING RULES" in system["content"]
    assert "VERBATIM" in system["content"]
    assert REAL_URL in user["content"]
    assert "OFFICIAL SOURCE EXCERPTS" in user["content"]


def test_without_passages_the_prompt_and_behaviour_are_unchanged(monkeypatch, groq_enabled, fake_chat):
    """An empty knowledge base must not change the pre-existing ungrounded path,
    including leaving the model's URLs alone — there is nothing to check against."""
    _with_passages(monkeypatch, [])
    steps, _reqs, passages = planner_mod._generate_custom_plan("widows pension")

    system, user = fake_chat["messages"]
    assert "GROUNDING RULES" not in system["content"]
    assert "OFFICIAL SOURCE EXCERPTS" not in user["content"]
    assert passages == []
    assert FAKE_URL in [s["source_url"] for s in steps]


def test_retrieval_failure_does_not_break_planning(monkeypatch):
    monkeypatch.setattr(
        retriever, "search", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("db down"))
    )
    context, passages = planner_mod._retrieval_context("widows pension")
    assert context == ""
    assert passages == []


def test_steps_carry_the_grounded_flag(monkeypatch, groq_enabled, fake_chat):
    _with_passages(monkeypatch, [PASSAGE])
    steps, _reqs, _p = planner_mod._generate_custom_plan("widows pension")
    assert steps[0]["grounded"] is True
    assert steps[2]["grounded"] is False


def test_planner_publishes_passages_for_the_knowledge_node(monkeypatch, groq_enabled, fake_chat):
    """The knowledge node reuses these instead of re-embedding the same goal."""
    _with_passages(monkeypatch, [PASSAGE])
    monkeypatch.setattr(planner_mod, "_keyword_plan", lambda _g: {"detected_services": [], "intent": {}})
    out = planner_mod.planner({"goal": "how do I claim a widows pension"})
    assert out["retrieved_passages"] == [PASSAGE]
    assert out["detected_services"] == ["custom_procedure"]
