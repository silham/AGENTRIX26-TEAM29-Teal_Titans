"""Eligibility Q&A flow: graph routing, structured questions, blocked alternatives."""
from app.graph.builder import _route_after_eligibility
from app.graph.nodes.checklist import _is_locked
from app.graph.nodes.eligibility import _question_fields


# ── Routing ───────────────────────────────────────────────────────────────────

def test_routes_to_ask_user_when_needs_info_and_interactive():
    state = {
        "interactive": True,
        "eligibility": {"overall": "needs_info"},
        "questions": ["What is your citizenship?"],
    }
    assert _route_after_eligibility(state) == "ask_user"


def test_routes_to_checklist_when_eligible():
    state = {
        "interactive": True,
        "eligibility": {"overall": "eligible"},
        "questions": [],
    }
    assert _route_after_eligibility(state) == "run_checklist"


def test_routes_to_checklist_when_not_interactive():
    """Without a checkpointer the graph cannot pause — never route to ask_user."""
    state = {
        "interactive": False,
        "eligibility": {"overall": "needs_info"},
        "questions": ["What is your citizenship?"],
    }
    assert _route_after_eligibility(state) == "run_checklist"


def test_routes_to_checklist_when_blocked():
    """Blocked is a final verdict — steps get locked with an alternative, no re-ask."""
    state = {
        "interactive": True,
        "eligibility": {"overall": "blocked"},
        "questions": [],
    }
    assert _route_after_eligibility(state) == "run_checklist"


# ── Structured questions ──────────────────────────────────────────────────────

_PROCS = {
    "svc": {
        "eligibility_rules": [
            {"field": "citizenship", "equals": "sri_lankan"},
            {"field": "has_existing_nic_number", "equals": True},
            {"field": "age", "min": 16},
        ]
    }
}


def test_question_fields_infer_input_types():
    fields = ["citizenship", "has_existing_nic_number", "age"]
    questions = ["Citizenship?", "Have NIC number?", "Age?"]
    specs = _question_fields(fields, questions, ["svc"], _PROCS)

    by_field = {s["field"]: s for s in specs}
    assert by_field["citizenship"]["type"] == "choice"
    assert {o["value"] for o in by_field["citizenship"]["options"]} == {"sri_lankan", "other"}
    assert by_field["has_existing_nic_number"]["type"] == "boolean"
    assert by_field["age"]["type"] == "number"


def test_question_fields_unknown_rule_falls_back_to_text():
    specs = _question_fields(["mystery"], ["Tell us?"], ["svc"], _PROCS)
    assert specs[0]["type"] == "text"


# ── Blocked lock reason includes the alternative ──────────────────────────────

def test_locked_reason_includes_alternative():
    elig_service = {
        "verdict": "blocked",
        "blockers": [{"field": "citizenship", "reason": "Requires citizenship to be sri_lankan."}],
        "alternative": "Apply for a residence visa at the Department of Immigration instead.",
    }
    locked, reason = _is_locked({"status": "ready"}, elig_service)
    assert locked
    assert "Requires citizenship" in reason
    assert "Alternative: Apply for a residence visa" in reason
