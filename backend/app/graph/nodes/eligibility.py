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


def _humanize(value: Any) -> str:
    return str(value).replace("_", " ").title()


def _find_rule(field: str, detected: list[str], procedures: dict[str, dict]) -> dict:
    for sid in detected:
        for rule in (procedures.get(sid) or {}).get("eligibility_rules", []) or []:
            if rule.get("field") == field:
                return rule
    return {}


def _question_fields(
    fields: list[str],
    questions: list[str],
    detected: list[str],
    procedures: dict[str, dict],
) -> list[dict[str, Any]]:
    """Structured question specs the UI renders as inputs.

    Input type is inferred from the rule that made the field necessary:
    equals-bool → yes/no, equals/in-str → choice (+ Other), min/max → number.
    """
    out: list[dict[str, Any]] = []
    for field, question in zip(fields, questions):
        rule = _find_rule(field, detected, procedures)
        spec: dict[str, Any] = {"field": field, "question": question, "type": "text"}
        if isinstance(rule.get("equals"), bool):
            spec["type"] = "boolean"
        elif isinstance(rule.get("equals"), str):
            spec["type"] = "choice"
            spec["options"] = [
                {"value": rule["equals"], "label": _humanize(rule["equals"])},
                {"value": "other", "label": "Other"},
            ]
        elif isinstance(rule.get("in"), list):
            spec["type"] = "choice"
            spec["options"] = [
                *({"value": v, "label": _humanize(v)} for v in rule["in"]),
                {"value": "other", "label": "Other"},
            ]
        elif "min" in rule or "max" in rule:
            spec["type"] = "number"
        out.append(spec)
    return out


def _alternative_path(service_name: str, reasons: list[str], goal: str) -> str:
    """Suggest a realistic alternate route for a citizen blocked from a service."""
    template = (
        f"You may not qualify for {service_name} ({'; '.join(reasons)}). "
        "Visit your nearest Divisional Secretariat to discuss alternative options "
        "for your situation."
    )
    if not settings.groq_api_key:
        return template
    # Generated in English, like everything else in the graph, and translated
    # at the API boundary. Asking the model to write Sinhala here produced
    # half-translated output and bypassed the glossary.
    sys = (
        "You advise Sri Lankan citizens who are NOT eligible for a government service. "
        "Suggest the most realistic alternative path in English, "
        "in 1-2 short sentences (mention the correct office/procedure if one exists). "
        'Respond ONLY with JSON: {"alternative": "..."}'
    )
    try:
        raw = chat(
            [
                {"role": "system", "content": sys},
                {
                    "role": "user",
                    "content": (
                        f"Goal: {goal}\nBlocked service: {service_name}\n"
                        f"Reason(s): {'; '.join(reasons)}"
                    ),
                },
            ],
            json_mode=True,
        )
        alt = json.loads(raw).get("alternative")
        if alt:
            return str(alt)
    except Exception:
        pass
    return template


def _phrase_questions(fields: list[str]) -> list[str]:
    """Phrase clarifying questions. Uses Groq when a key is configured, else
    falls back to deterministic templates (keeps unit tests offline)."""
    if not fields:
        return []
    templates = [_template_question(f) for f in fields]
    if not settings.groq_api_key:
        return templates

    sys = (
        "You phrase short, polite clarifying questions in English for a Sri Lankan "
        "citizen services assistant. "
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


_ALWAYS_ELIGIBLE = {
    "overall": "eligible",
    "services": {"custom_procedure": {"verdict": "eligible", "blockers": [], "missing_facts": []}},
}

_CUSTOM_QUESTIONS_SYS = """\
You screen Sri Lankan citizens for eligibility before they start a government procedure.
Given the citizen's goal and the procedure steps, produce the MINIMAL set of clarifying
questions (1-4) whose answers determine whether this citizen can actually do this
procedure. Only ask what changes eligibility (citizenship/residency status, legal
relationships, age, ownership, prior registrations). Do not ask for documents or dates.

Respond ONLY with JSON, in English:
{{
  "questions": [
    {{
      "field": "<snake_case_key>",
      "question": "<short question>",
      "type": "choice" | "boolean" | "number",
      "options": ["<option 1>", "<option 2>", ...]   // only for type "choice", 2-4 options
    }}
  ]
}}

If nothing about this goal could make a citizen ineligible, return {{"questions": []}}.\
"""

_CUSTOM_VERDICT_SYS = """\
You decide whether a Sri Lankan citizen is eligible for a government procedure,
based on their answers to screening questions. Be practical: block only when an
answer clearly disqualifies them under normal Sri Lankan rules.

Every question HAS been answered — "No" is a real answer, never treat it as
missing information, and never block because something was "not provided".

Respond ONLY with JSON:
{
  "eligible": true | false,
  "reasons": ["<short reason per problem>"],          // empty when eligible
  "alternative": "<1-2 sentence realistic alternative path in Sri Lanka, or null>"
}\
"""


def _fmt_answer(value: Any) -> Any:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return value


def _custom_eligibility(
    goal: str,
    custom_steps: list[dict],
    facts: dict[str, Any],
    asked_fields: list[dict],
) -> tuple[dict, list[str], list[dict]]:
    """LLM-driven eligibility for custom procedures.

    No facts yet → generate screening questions on the fly (needs_info pauses
    the graph). Facts present → evaluate them for a verdict. Any LLM failure
    degrades to "eligible" so a custom case is never dead-ended by an outage.
    Returns (eligibility_dict, questions, question_fields).
    """
    if not settings.groq_api_key:
        return _ALWAYS_ELIGIBLE, [], []

    step_titles = "; ".join(s.get("title", "") for s in (custom_steps or [])[:8])

    if not facts:
        try:
            raw = chat(
                [
                    # .format() with no args still unescapes the {{ }} braces
                    # that keep the JSON example literal in the prompt.
                    {"role": "system", "content": _CUSTOM_QUESTIONS_SYS.format()},
                    {"role": "user", "content": f"Goal: {goal}\nProcedure steps: {step_titles}"},
                ],
                json_mode=True,
            )
            items = json.loads(raw).get("questions") or []
        except Exception:
            return _ALWAYS_ELIGIBLE, [], []

        questions: list[str] = []
        question_fields: list[dict[str, Any]] = []
        for it in items[:4]:
            field, question = it.get("field"), it.get("question")
            if not field or not question:
                continue
            qtype = it.get("type") if it.get("type") in ("choice", "boolean", "number") else "text"
            spec: dict[str, Any] = {"field": str(field), "question": str(question), "type": qtype}
            if qtype == "choice":
                opts = [str(o) for o in (it.get("options") or []) if o][:4]
                if not opts:
                    spec["type"] = "text"
                else:
                    spec["options"] = [{"value": o, "label": _humanize(o)} for o in opts]
            question_fields.append(spec)
            questions.append(str(question))

        if not question_fields:
            return _ALWAYS_ELIGIBLE, [], []
        verdict = {
            "overall": "needs_info",
            "services": {
                "custom_procedure": {
                    "verdict": "needs_info",
                    "blockers": [],
                    "missing_facts": [q["field"] for q in question_fields],
                }
            },
        }
        return verdict, questions, question_fields

    # Facts answered → evaluate. Send question TEXT with each answer so the
    # model reads booleans correctly ("No, not a minor" ≠ "age not provided").
    asked = {q["field"]: q["question"] for q in asked_fields or []}
    qa_lines = [
        f"Q: {asked.get(field, field.replace('_', ' '))}  A: {_fmt_answer(value)}"
        for field, value in facts.items()
    ]
    try:
        raw = chat(
            [
                {"role": "system", "content": _CUSTOM_VERDICT_SYS},
                {
                    "role": "user",
                    "content": (
                        f"Goal: {goal}\nProcedure steps: {step_titles}\n"
                        "Screening answers:\n" + "\n".join(qa_lines)
                    ),
                },
            ],
            json_mode=True,
        )
        data = json.loads(raw)
    except Exception:
        return _ALWAYS_ELIGIBLE, [], []

    if data.get("eligible", True):
        return _ALWAYS_ELIGIBLE, [], []

    reasons = [str(r) for r in (data.get("reasons") or [])] or ["You may not qualify for this procedure."]
    svc: dict[str, Any] = {
        "verdict": "blocked",
        "blockers": [{"field": "custom", "reason": r} for r in reasons],
        "missing_facts": [],
    }
    if data.get("alternative"):
        svc["alternative"] = str(data["alternative"])
    return {"overall": "blocked", "services": {"custom_procedure": svc}}, [], []


def eligibility(state: GraphState) -> dict:
    detected = state.get("detected_services", []) or []
    facts = dict(state.get("facts", {}) or {})

    # Custom goals have no rules JSON — Groq generates the screening questions
    # on the fly, and (once answered) judges the answers for a verdict.
    if detected == ["custom_procedure"]:
        verdict, questions, question_fields = _custom_eligibility(
            state.get("goal", ""),
            state.get("custom_steps") or [],
            facts,
            state.get("question_fields") or [],
        )
        svc = verdict["services"]["custom_procedure"]
        alternatives = (
            [{
                "service": "custom_procedure",
                "name": "this procedure",
                "reason": "; ".join(b["reason"] for b in svc["blockers"]),
                "alternative": svc.get("alternative"),
            }]
            if svc["verdict"] == "blocked" else []
        )
        log_update = audit(
            state,
            agent="eligibility",
            decision=f"Eligibility (LLM): {verdict['overall']}",
            reason=(
                f"asked: {[q['field'] for q in question_fields]}" if question_fields
                else "; ".join(b["reason"] for b in svc["blockers"]) if svc["blockers"]
                else "LLM-assessed eligibility for custom procedure"
            ),
            confidence=0.75,
        )
        return {
            "eligibility": verdict,
            "questions": questions,
            "question_fields": question_fields,
            "alternatives": alternatives,
            **log_update,
        }

    procedures = load_procedures()
    verdict, missing = evaluate_eligibility(detected, procedures, facts)
    questions = _phrase_questions(missing)
    question_fields = _question_fields(missing, questions, detected, procedures)

    # Blocked service → suggest an alternate route (embedded per-service so the
    # checklist can surface it in the locked step's reason).
    alternatives: list[dict[str, Any]] = []
    for sid, svc in verdict["services"].items():
        if svc["verdict"] != "blocked":
            continue
        name = (procedures.get(sid) or {}).get("name", sid)
        reasons = [b["reason"] for b in svc["blockers"]]
        alt = _alternative_path(name, reasons, state.get("goal", ""))
        svc["alternative"] = alt
        alternatives.append({"service": sid, "name": name, "reason": "; ".join(reasons), "alternative": alt})

    log_update = audit(
        state,
        agent="eligibility",
        decision=f"Eligibility: {verdict['overall']}"
                 + (f" — alternatives suggested for {[a['service'] for a in alternatives]}" if alternatives else ""),
        reason=(
            f"missing facts: {missing}" if missing
            else alternatives[0]["reason"] if alternatives
            else "all eligibility rules satisfied"
        ),
        confidence=1.0,  # rule-based, deterministic
    )

    return {
        "eligibility": verdict,
        "questions": questions,
        "question_fields": question_fields,
        "alternatives": alternatives,
        **log_update,
    }
