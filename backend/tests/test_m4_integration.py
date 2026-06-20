"""M3 + M4 integration — the headline "lost NIC → passport" flow.

Chains the REAL dependency node (M3) → eligibility (M4) → checklist (M4) against
the real rules layer (data/procedures/*.json). No DB, no LLM: dependency and
eligibility are deterministic, and checklist persistence is skipped without a
case_id. This proves M4 consumes M3's actual dependency_graph + rules.steps shapes.

Run with:  pytest tests/test_m4_integration.py -v
"""
from __future__ import annotations

from app.graph.nodes.checklist import checklist
from app.graph.nodes.dependency import dependency
from app.graph.nodes.eligibility import eligibility

_SERVICES = ["passport_application", "duplicate_nic"]
_FACTS = {"citizenship": "sri_lankan", "age": 30, "has_existing_nic_number": True}


def _run_flow():
    state: dict = {
        "detected_services": _SERVICES,
        "intent": {"missing_requirements": ["valid_nic"]},
        "facts": _FACTS,
        "documents": [],
        "logs": [],
    }
    state.update(dependency(state))
    state.update(eligibility(state))
    state.update(checklist(state))
    return state


def test_dependency_locks_passport_behind_nic():
    state = _run_flow()
    services = state["dependency_graph"]["services"]
    assert services["passport_application"]["status"] == "locked"
    assert "duplicate_nic" in services["passport_application"]["blocked_by"]
    assert services["duplicate_nic"]["status"] == "ready"


def test_eligibility_eligible_with_full_facts():
    state = _run_flow()
    assert state["eligibility"]["overall"] == "eligible"
    assert state["questions"] == []


def test_checklist_orders_nic_first_and_locks_passport():
    state = _run_flow()
    items = state["checklist"]

    # Real rules: 6 duplicate_nic steps + 7 passport steps.
    assert len(items) == 13

    passport = [it for it in items if it["service"] == "passport_application"]
    assert passport and all(it["status"] == "locked" for it in passport)
    assert all(it["reason"] for it in passport)  # lock reason carried through

    # The single next best action is the first duplicate-NIC step.
    active = [it for it in items if it["status"] == "active"]
    assert len(active) == 1
    assert active[0]["service"] == "duplicate_nic"
    assert active[0]["ord"] == 0
    assert state["progress"] == 0


def test_accepted_documents_advance_progress():
    """Accepting the duplicate-NIC requirement should unlock + progress the plan."""
    state: dict = {
        "detected_services": _SERVICES,
        # NIC now satisfied → passport no longer locked by dependency.
        "intent": {"satisfied_requirements": ["valid_nic"]},
        "facts": _FACTS,
        "documents": [],
        "logs": [],
    }
    state.update(dependency(state))
    state.update(eligibility(state))
    state.update(checklist(state))

    passport = [it for it in state["checklist"] if it["service"] == "passport_application"]
    assert not any(it["status"] == "locked" for it in passport), "passport should be unlocked"
