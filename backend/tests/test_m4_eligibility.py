"""M4 tests — eligibility node (deterministic rules + minimal questions).

Run with:  pytest tests/test_m4_eligibility.py -v

No Groq key is needed: with settings.groq_api_key == "" the node falls back to
templated questions, so these tests are fully offline.
"""
from __future__ import annotations

import app.graph.nodes.eligibility as elig_mod
from app.graph.nodes.eligibility import _check_rule, evaluate_eligibility
from tests.m4_fixtures import procedures


# ── Pure rule evaluation ──────────────────────────────────────────────────────


def test_eligible_when_facts_satisfy_rules():
    verdict, missing = evaluate_eligibility(
        ["duplicate_nic", "passport_application"], procedures(), {"citizenship": "sri_lankan"}
    )
    assert verdict["overall"] == "eligible"
    assert missing == []
    assert verdict["services"]["passport_application"]["verdict"] == "eligible"


def test_needs_info_when_fact_unknown():
    verdict, missing = evaluate_eligibility(["passport_application"], procedures(), {})
    assert verdict["overall"] == "needs_info"
    assert "citizenship" in missing
    assert verdict["services"]["passport_application"]["missing_facts"] == ["citizenship"]


def test_blocked_when_fact_fails_rule():
    verdict, missing = evaluate_eligibility(
        ["passport_application"], procedures(), {"citizenship": "indian"}
    )
    assert verdict["overall"] == "blocked"
    assert missing == []
    svc = verdict["services"]["passport_application"]
    assert svc["verdict"] == "blocked"
    assert svc["blockers"] and svc["blockers"][0]["field"] == "citizenship"


def test_missing_fields_deduplicated_across_services():
    _, missing = evaluate_eligibility(
        ["duplicate_nic", "passport_application"], procedures(), {}
    )
    assert missing == ["citizenship"]  # asked once, not per service


def test_check_rule_operators():
    assert _check_rule({"field": "age", "min": 18}, 21) is True
    assert _check_rule({"field": "age", "min": 18}, 16) is False
    assert _check_rule({"field": "age", "max": 60}, 70) is False
    assert _check_rule({"field": "x", "in": ["a", "b"]}, "a") is True
    assert _check_rule({"field": "x", "not_equals": "z"}, "y") is True
    assert _check_rule({"field": "x", "min": 18}, "not-a-number") is False
    assert _check_rule({"field": "x"}, "anything") is True  # no operator → pass


# ── Node wrapper ──────────────────────────────────────────────────────────────


def test_node_returns_questions_and_log(monkeypatch):
    monkeypatch.setattr(elig_mod, "load_procedures", procedures)
    state = {
        "detected_services": ["duplicate_nic", "passport_application"],
        "facts": {},
        "language": "en",
        "logs": [],
    }
    result = elig_mod.eligibility(state)

    assert result["eligibility"]["overall"] == "needs_info"
    assert len(result["questions"]) == 1  # one dedup'd question for citizenship
    assert result["logs"][-1]["agent"] == "eligibility"


def test_node_eligible_has_no_questions(monkeypatch):
    monkeypatch.setattr(elig_mod, "load_procedures", procedures)
    state = {
        "detected_services": ["passport_application"],
        "facts": {"citizenship": "sri_lankan"},
        "logs": [],
    }
    result = elig_mod.eligibility(state)
    assert result["eligibility"]["overall"] == "eligible"
    assert result["questions"] == []
