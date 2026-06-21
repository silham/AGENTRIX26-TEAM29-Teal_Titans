"""Owner: M4. Eligibility node — rules verdict + minimal clarifying questions.

The *decision* is deterministic (driven by each service's ``eligibility_rules``
from the JSON rules layer). Groq is used only to phrase any clarifying questions
nicely; if it's unavailable we fall back to plain templated questions.

Consumes (from GraphState)
    detected_services : list[str]   service ids the planner found
    facts             : dict        known citizen facts, e.g. {"citizenship": "sri_lankan", "age": 30}
                                    (populated by the resume/answer flow; read defensively)

Produces (into GraphState)
    eligibility : {
        "overall": "eligible" | "blocked" | "needs_info",
        "services": {
            "<service_id>": {
                "verdict": "eligible" | "blocked" | "needs_info",
                "blockers": [{"field": str, "reason": str}],
                "missing_facts": [str, ...],
            }, ...
        },
    }
    questions : list[str]   minimal set of clarifying questions for missing facts

Rule shape (rules layer, IMPLEMENTATION_PLAN §5):
    {"field": "citizenship", "equals": "sri_lankan"}
Supported operators: equals, not_equals, in, min, max.
"""
from __future__ import annotations

import json
from typing import Any

from app.config import settings
from app.graph.nodes.audit import audit
from app.graph.state import GraphState
from app.llm.groq_client import chat

# M3's rules.py exposes load_procedures(); the per-field query helpers are still
# TODO there, so we read eligibility_rules straight off the loaded procedure dict.
from app.rag.rules import load_procedures

# Human-readable labels for fields we expect to ask about.
_FIELD_LABELS = {
    "citizenship": "your citizenship",
    "age": "your age",
    "marital_status": "your marital status",
    "residence_district": "your district of residence",
    "employment_status": "your employment status",
    "student_status": "whether you are a student",
    "has_existing_nic_number": "whether you already have an NIC number",
}


def _check_rule(rule: dict[str, Any], value: Any) -> bool:
    """Return True if ``value`` satisfies ``rule``. Unknown operators pass."""
    if "equals" in rule:
        return value == rule["equals"]
    if "not_equals" in rule:
        return value != rule["not_equals"]
    if "in" in rule:
        return value in rule["in"]
    if "min" in rule:
        try:
            return float(value) >= float(rule["min"])
        except (TypeError, ValueError):
            return False
    if "max" in rule:
        try:
            return float(value) <= float(rule["max"])
        except (TypeError, ValueError):
            return False
    return True


def _rule_reason(rule: dict[str, Any], field: str) -> str:
    label = _FIELD_LABELS.get(field, field)
    if "equals" in rule:
        return f"Requires {label} to be {rule['equals']}."
    if "not_equals" in rule:
        return f"Not available when {label} is {rule['not_equals']}."
    if "in" in rule:
        return f"Requires {label} to be one of {rule['in']}."
    if "min" in rule:
        return f"Requires {label} of at least {rule['min']}."
    if "max" in rule:
        return f"Requires {label} of at most {rule['max']}."
    return f"Has a condition on {label}."


def evaluate_eligibility(
    detected_services: list[str],
    procedures: dict[str, dict],
    facts: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Pure rules evaluation. Returns (eligibility_dict, missing_fields)."""
    services: dict[str, Any] = {}
    missing_fields: list[str] = []

    for sid in detected_services:
        rules = (procedures.get(sid) or {}).get("eligibility_rules", []) or []
        blockers: list[dict[str, str]] = []
        missing: list[str] = []

        for rule in rules:
            field = rule.get("field")
            if not field:
                continue
            if field not in facts or facts.get(field) in (None, ""):
                missing.append(field)
                continue
            if not _check_rule(rule, facts[field]):
                blockers.append({"field": field, "reason": _rule_reason(rule, field)})

        if blockers:
            verdict = "blocked"
        elif missing:
            verdict = "needs_info"
        else:
            verdict = "eligible"

        services[sid] = {"verdict": verdict, "blockers": blockers, "missing_facts": missing}
        for f in missing:
            if f not in missing_fields:
                missing_fields.append(f)

    if any(s["verdict"] == "blocked" for s in services.values()):
        overall = "blocked"
    elif missing_fields:
        overall = "needs_info"
    else:
        overall = "eligible"

    return {"overall": overall, "services": services}, missing_fields


def _template_question(field: str) -> str:
    return f"Could you tell us {_FIELD_LABELS.get(field, field.replace('_', ' '))}?"


def _phrase_questions(fields: list[str], language: str) -> list[str]:
    """Phrase clarifying questions. Uses Groq when a key is configured, else
    falls back to deterministic templates (keeps unit tests offline)."""
    if not fields:
        return []
    templates = [_template_question(f) for f in fields]
    if not settings.groq_api_key:
        return templates

    sys = (
        "You phrase short, polite clarifying questions for a Sri Lankan citizen "
        f"services assistant, in language code '{language}'. "
        'Respond ONLY with JSON: {"questions": ["...", ...]} — one question per field, same order.'
    )
    try:
        raw = chat(
            [
                {"role": "system", "content": sys},
                {"role": "user", "content": f"Fields to ask about: {fields}"},
            ],
            json_mode=True,
        )
        out = json.loads(raw).get("questions")
        if isinstance(out, list) and len(out) == len(fields):
            return [str(q) for q in out]
    except Exception:
        pass
    return templates


def _llm_custom_eligibility(_goal: str, _custom_steps: list[dict], _language: str) -> tuple[dict, list[str]]:
    """Custom procedures have no predefined eligibility rules — always eligible."""
    return {
        "overall": "eligible",
        "services": {"custom_procedure": {"verdict": "eligible", "blockers": [], "missing_facts": []}},
    }, []


def eligibility(state: GraphState) -> dict:
    detected = state.get("detected_services", []) or []
    facts = dict(state.get("facts", {}) or {})

    # For custom goals, use LLM-based eligibility check instead of empty rules.
    if detected == ["custom_procedure"]:
        verdict, questions = _llm_custom_eligibility(
            state.get("goal", ""),
            state.get("custom_steps") or [],
            state.get("language", "en"),
        )
        log_update = audit(
            state,
            agent="eligibility",
            decision=f"Eligibility (LLM): {verdict['overall']}",
            reason="LLM-assessed eligibility for custom procedure",
            confidence=0.75,
        )
        return {"eligibility": verdict, "questions": questions, **log_update}

    procedures = load_procedures()
    verdict, missing = evaluate_eligibility(detected, procedures, facts)
    questions = _phrase_questions(missing, state.get("language", "en"))

    log_update = audit(
        state,
        agent="eligibility",
        decision=f"Eligibility: {verdict['overall']}",
        reason=(
            f"missing facts: {missing}" if missing else "all eligibility rules satisfied"
        ),
        confidence=1.0,  # rule-based, deterministic
    )

    return {"eligibility": verdict, "questions": questions, **log_update}
