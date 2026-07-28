"""The value/label hazard — the highest-stakes property in the i18n layer.

Eligibility options carry a MACHINE KEY in `value` and display text in `label`.
`_check_rule` compares those values with exact `==` against English strings from
the procedure JSON. If translation ever touched a `value`, an eligible citizen
would be told they do not qualify — a silent denial with no error anywhere.

These tests exist to make that failure impossible to reintroduce.
"""
from __future__ import annotations

import pytest

from app.graph.nodes.eligibility import (
    _question_fields,
    evaluate_eligibility,
)
from app.graph.runner import _localize_question_fields
from app.rag.rules import load_procedures


@pytest.fixture
def fake_translate(monkeypatch):
    """Translate by tagging, so any leaked translation is unmistakable."""
    calls: list[list[str]] = []

    def _tr(texts, lang, *, cache_only=False):
        calls.append(list(texts))
        return {t: f"[{lang}]{t}" for t in texts}

    monkeypatch.setattr("app.graph.runner.translate_many", _tr)
    return calls


# ── rules path: value comes from the procedure JSON ─────────────────────────


def _passport_specs() -> list[dict]:
    """Every field passport_application screens on, as the graph would ask it.

    All of them, not just citizenship: `evaluate_eligibility` reports any
    unanswered field as missing, so a partial fixture cannot show a clean pass.
    """
    procedures = load_procedures()
    fields = [
        r["field"]
        for r in procedures["passport_application"].get("eligibility_rules", [])
        if r.get("field")
    ]
    questions = [f"What is your {f.replace('_', ' ')}?" for f in fields]
    return _question_fields(fields, questions, ["passport_application"], procedures)


def test_rules_path_option_values_are_never_translated(fake_translate):
    specs = _passport_specs()
    citizenship = next(s for s in specs if s["field"] == "citizenship")
    assert citizenship["type"] == "choice", "fixture assumes a choice question"

    out = _localize_question_fields(specs, "si")
    citizenship_out = next(s for s in out if s["field"] == "citizenship")

    values = [o["value"] for o in citizenship_out["options"]]
    assert "sri_lankan" in values
    assert all(not v.startswith("[si]") for v in values)
    # Field keys are posted back verbatim too, so they must survive as well.
    assert {s["field"] for s in out} == {s["field"] for s in specs}


def test_rules_path_labels_and_question_are_translated(fake_translate):
    out = _localize_question_fields(_passport_specs(), "si")
    citizenship = next(s for s in out if s["field"] == "citizenship")

    assert citizenship["question"].startswith("[si]")
    assert all(o["label"].startswith("[si]") for o in citizenship["options"])


def test_answer_roundtrip_still_evaluates_eligible(fake_translate):
    """The regression that would silently deny citizens their plans.

    Simulates the full loop: questions are localized, the browser posts back
    the `value`/`field` it was given, and eligibility must still pass.
    """
    localized = _localize_question_fields(_passport_specs(), "si")

    # Exactly what the frontend submits: opt.value and q.field, untouched.
    facts: dict = {}
    for spec in localized:
        if spec["type"] == "choice":
            facts[spec["field"]] = spec["options"][0]["value"]
        elif spec["type"] == "number":
            facts[spec["field"]] = 30
        elif spec["type"] == "boolean":
            facts[spec["field"]] = True
        else:
            facts[spec["field"]] = "yes"

    verdict, missing = evaluate_eligibility(
        ["passport_application"], load_procedures(), facts
    )
    assert missing == [], "a localized question left a field unanswerable"
    assert verdict["services"]["passport_application"]["verdict"] != "blocked"


# ── custom path: value IS the LLM-generated display string ──────────────────


def test_custom_path_option_values_are_never_translated(fake_translate):
    """In the custom path `value` and `label` derive from the same LLM string.

    That makes it far easier to translate the value by accident than in the
    rules path, so it gets its own test.
    """
    specs = [
        {
            "field": "owns_property",
            "question": "Do you own the property?",
            "type": "choice",
            "options": [
                {"value": "yes_sole_owner", "label": "Yes Sole Owner"},
                {"value": "no", "label": "No"},
            ],
        }
    ]
    out = _localize_question_fields(specs, "ta")

    assert [o["value"] for o in out[0]["options"]] == ["yes_sole_owner", "no"]
    assert out[0]["field"] == "owns_property"
    assert all(o["label"].startswith("[ta]") for o in out[0]["options"])


def test_localizing_does_not_mutate_the_source_specs(fake_translate):
    """`question_fields` may alias the LangGraph checkpoint's own list.

    Mutating it in place would leave Sinhala questions in graph state, which
    are then replayed into the English-only verdict prompt on resume.
    """
    specs = [
        {
            "field": "citizenship",
            "question": "What is your citizenship?",
            "type": "choice",
            "options": [{"value": "sri_lankan", "label": "Sri Lankan"}],
        }
    ]
    out = _localize_question_fields(specs, "si")

    assert specs[0]["question"] == "What is your citizenship?"
    assert specs[0]["options"][0]["label"] == "Sri Lankan"
    assert out[0]["question"].startswith("[si]"), "the copy should be translated"


def test_english_makes_no_translation_call(fake_translate):
    specs = _passport_specs()
    out = _localize_question_fields(specs, "en")
    assert fake_translate == []
    assert out[0]["question"] == specs[0]["question"]


def test_number_and_boolean_specs_survive(fake_translate):
    specs = [
        {"field": "age", "question": "How old are you?", "type": "number"},
        {"field": "has_nic", "question": "Do you have an NIC?", "type": "boolean"},
    ]
    out = _localize_question_fields(specs, "si")

    assert [s["field"] for s in out] == ["age", "has_nic"]
    assert [s["type"] for s in out] == ["number", "boolean"]
    assert all(s["question"].startswith("[si]") for s in out)
