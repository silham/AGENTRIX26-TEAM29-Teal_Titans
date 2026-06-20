"""Owner: M2. Planner node — goal → detected services + intent (Groq)."""
import json

from app.graph.nodes.audit import audit
from app.graph.state import GraphState
from app.llm.groq_client import chat

_SYSTEM = """\
You are a Sri Lankan government services planner.
Given a citizen's natural-language goal, identify which government services are required
and characterise the intent.

Respond ONLY with a valid JSON object in this exact shape:
{
  "detected_services": ["<service_id>", ...],
  "intent": {
    "primary_goal": "<one-line description>",
    "urgency": "low|medium|high",
    "has_blocking_issues": true|false,
    "blocking_issues": ["<issue>"]
  }
}

Known service IDs: passport_application, duplicate_nic, driving_license_renewal,
birth_certificate_copy, marriage_registration, business_registration,
document_emergency_recovery.\
"""


def planner(state: GraphState) -> dict:
    goal = state.get("goal", "")
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": f"Citizen goal: {goal}"},
    ]

    raw = chat(messages, json_mode=True)
    try:
        result: dict = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        result = {"detected_services": [], "intent": {}}

    log_update = audit(
        state,
        agent="planner",
        decision=f"Detected services: {result.get('detected_services', [])}",
        reason=goal,
        confidence=0.9,
    )

    return {
        "detected_services": result.get("detected_services", []),
        "intent": result.get("intent", {}),
        **log_update,
    }
