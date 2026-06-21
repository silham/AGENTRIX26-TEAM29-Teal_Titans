"""Owner: M2. Planner node — goal → detected services + intent (Groq + keyword fallback).

For goals that match no known procedure JSON, Groq generates a custom step-by-step
plan directly and stores it in state["custom_steps"] with service id "custom_procedure".
The checklist node reads custom_steps when no rules-based steps exist.
"""
from __future__ import annotations

import json
import re

from app.config import settings
from app.graph.nodes.audit import audit
from app.graph.state import GraphState
from app.rag import rules

# ── Service detection prompt ──────────────────────────────────────────────────

_SYSTEM = """\
You are a Sri Lankan government services planner.
Given a citizen's natural-language goal, identify which government services are required
and characterise the intent — including what documents/items the citizen already has and
what they are missing or have lost.

Respond ONLY with a valid JSON object in this exact shape:
{
  "detected_services": ["<service_id>", ...],
  "intent": {
    "primary_goal": "<one-line description>",
    "urgency": "low|medium|high",
    "has_blocking_issues": true|false,
    "blocking_issues": ["<issue>"],
    "have": ["<requirement_key>", ...],
    "missing": ["<requirement_key>", ...],
    "lost": ["<requirement_key>", ...]
  }
}

Requirement keys: valid_nic, birth_certificate, passport, driving_license, police_report,
marriage_certificate, business_registration_certificate.

Rules:
- If the citizen says they LOST their NIC/identity card, add "valid_nic" to "lost" AND
  "missing", and include "duplicate_nic" in detected_services BEFORE passport_application.
- If the citizen says they HAVE a document, add its key to "have".
- If a service requires an NIC and the citizen has not confirmed they have one, add
  "valid_nic" to "missing".
- Always list prerequisite services BEFORE the services that depend on them.
- "lost" means the citizen explicitly said something is lost/stolen/destroyed.
- "missing" means the citizen doesn't have it (whether lost or never had).

Known service IDs: passport_application, duplicate_nic, driving_license_renewal,
birth_certificate_copy, marriage_registration, business_registration,
document_emergency_recovery.\
"""

# ── Custom procedure generation prompt ───────────────────────────────────────

_CUSTOM_SYSTEM = """\
You are an expert on Sri Lankan government procedures and legal processes.
A citizen has a goal that does not match any of our pre-defined service workflows.
Generate a clear, practical, step-by-step procedure guide for Sri Lanka.

Respond ONLY with valid JSON in this exact shape:
{
  "service_name": "<short name for this procedure>",
  "office": "<primary government office or department>",
  "steps": [
    {
      "title": "<short action title>",
      "description": "<clear explanation of what to do, who to contact, what documents to bring>",
      "source_url": "<official Sri Lanka government URL if known, else null>"
    }
  ],
  "requirements": ["<document or item needed>", ...]
}

Rules:
- Be specific to Sri Lanka (offices, forms, departments).
- List steps in the correct order the citizen must follow.
- Include realistic document requirements.
- Keep each step title under 10 words.
- Maximum 10 steps.
- Use null for source_url when unsure — do NOT invent URLs.\
"""

# ── Keyword fallback (no Groq key needed) ────────────────────────────────────

_KEYWORD_MAP: list[tuple[list[str], str]] = [
    (["passport", "travel document", "go abroad", "visa"], "passport_application"),
    (["nic", "national identity", "identity card", "id card"], "duplicate_nic"),
    (["driving licen", "driver licen", "license renewal", "licence renewal", "driving test"], "driving_license_renewal"),
    (["birth certificate", "birth cert", "birth cert"], "birth_certificate_copy"),
    (["marriage", "wed", "nikah", "get married"], "marriage_registration"),
    (["business", "company", "shop", "trade license", "sole proprietor", "entrepreneur"], "business_registration"),
    (["flood", "fire", "theft", "all documents", "lost documents", "lost all", "disaster"], "document_emergency_recovery"),
]

_LOST_PATTERNS = [
    r"\blost\b", r"\bmissing\b", r"\bstolen\b", r"\bdamaged\b",
    r"\bcannot find\b", r"can'?t find", r"\bno longer have\b",
]

_NIC_PATTERNS = [r"\bnic\b", r"national identity", r"identity card", r"id card"]


def _keyword_plan(goal: str) -> dict:
    """Rule-based service detection when Groq is unavailable or produces no valid IDs."""
    lower = goal.lower()

    detected: list[str] = []
    for patterns, service in _KEYWORD_MAP:
        # Only accept keyword matches for services that have a rules JSON with steps.
        if any(p in lower for p in patterns) and rules.steps(service):
            detected.append(service)

    # Dedup while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for s in detected:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    detected = unique

    # Detect lost/missing NIC
    is_lost = any(re.search(p, lower) for p in _LOST_PATTERNS)
    nic_mentioned = any(re.search(p, lower) for p in _NIC_PATTERNS)
    lost_nic = is_lost and nic_mentioned

    lost: list[str] = []
    missing: list[str] = []
    have: list[str] = []

    if lost_nic:
        lost.append("valid_nic")
        missing.append("valid_nic")
        if "duplicate_nic" not in detected:
            detected.insert(0, "duplicate_nic")
        if "passport_application" in detected:
            detected = [s for s in detected if s != "duplicate_nic"]
            passport_idx = detected.index("passport_application")
            detected.insert(passport_idx, "duplicate_nic")

    if "passport_application" in detected and "valid_nic" not in have:
        if "valid_nic" not in missing:
            missing.append("valid_nic")

    if "document_emergency_recovery" in detected:
        lost.extend(["valid_nic", "birth_certificate", "passport"])
        missing.extend(["valid_nic", "birth_certificate", "passport"])

    urgency = "high" if (is_lost or "document_emergency_recovery" in detected) else "medium"

    return {
        "detected_services": detected,  # empty list = unknown goal → custom plan
        "intent": {
            "primary_goal": goal[:120],
            "urgency": urgency,
            "has_blocking_issues": bool(lost),
            "blocking_issues": [f"Lost: {', '.join(lost)}"] if lost else [],
            "have": have,
            "missing": list(set(missing)),
            "lost": list(set(lost)),
        },
    }


def _generate_custom_plan(goal: str) -> tuple[list[dict], list[str]]:
    """Ask Groq to generate a full plan (steps + requirements) for an unknown goal.

    Returns (steps, requirements). steps are compatible with rules.steps() output.
    Both lists are empty on failure.
    """
    import sys
    if not settings.groq_api_key:
        return [], []
    from app.llm.groq_client import chat
    try:
        raw = chat(
            [
                {"role": "system", "content": _CUSTOM_SYSTEM},
                {"role": "user", "content": f"Citizen goal: {goal}"},
            ],
            json_mode=True,
        )
        data = json.loads(raw)
        raw_steps = data.get("steps") or []
        steps = [
            {
                "title": str(s.get("title", "")),
                "description": s.get("description") or None,
                "source_url": s.get("source_url") or None,
                "fulfills": None,
                "_service_name": data.get("service_name", "Custom Procedure"),
                "_office": data.get("office", ""),
            }
            for s in raw_steps
            if s.get("title")
        ]
        requirements = [str(r) for r in (data.get("requirements") or []) if r]
        return steps, requirements
    except Exception as exc:
        print(f"[planner] _generate_custom_plan failed: {exc!r}", file=sys.stderr)
        return [], []


def planner(state: GraphState) -> dict:
    goal = state.get("goal", "")
    result: dict = {}
    custom_steps: list[dict] = []
    custom_requirements: list[str] = []

    # ── Try Groq for service detection ───────────────────────────────────────
    if settings.groq_api_key:
        from app.llm.groq_client import chat
        try:
            raw = chat(
                [
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": f"Citizen goal: {goal}"},
                ],
                json_mode=True,
            )
            parsed = json.loads(raw)
            # Keep only known IDs that also have a rules JSON file with actual steps.
            # Services without steps (no JSON file yet) are treated as unrecognised so
            # the goal falls through to the custom Groq plan generator.
            raw_services = parsed.get("detected_services") or []
            valid = [s for s in raw_services if rules.steps(s)]
            if valid:
                parsed["detected_services"] = valid
                result = parsed
        except Exception:
            result = {}

    # ── Keyword fallback when Groq failed or produced no valid services ───────
    if not result.get("detected_services"):
        result = _keyword_plan(goal)

    # ── Custom Groq-generated plan for goals with no matching service ─────────
    if not result.get("detected_services"):
        custom_steps, custom_requirements = _generate_custom_plan(goal)
        if custom_steps:
            result["detected_services"] = ["custom_procedure"]
            if not result.get("intent"):
                result["intent"] = {
                    "primary_goal": goal[:120],
                    "urgency": "medium",
                    "has_blocking_issues": False,
                    "blocking_issues": [],
                    "have": [],
                    "missing": [],
                    "lost": [],
                }

    services = result.get("detected_services", [])
    confidence = 0.95 if (services and services != ["custom_procedure"] and settings.groq_api_key) \
        else 0.8 if custom_steps \
        else 0.7

    log_update = audit(
        state,
        agent="planner",
        decision=f"Detected services: {services}"
                 + (" (custom Groq plan)" if custom_steps else ""),
        reason=goal,
        confidence=confidence,
    )

    return {
        "detected_services": services,
        "intent": result.get("intent", {}),
        "custom_steps": custom_steps,
        "custom_requirements": custom_requirements,
        **log_update,
    }
