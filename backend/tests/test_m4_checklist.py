"""M4 tests — checklist node (ordering, locking, progress, persistence).

Run with:  pytest tests/test_m4_checklist.py -v
"""
from __future__ import annotations

from uuid import uuid4

import app.graph.nodes.checklist as cl_mod
from app.graph.nodes.checklist import _STEP_COLUMNS, compose_checklist
from tests.m4_fixtures import dependency_graph, eligibility_eligible


# ── Pure composition ──────────────────────────────────────────────────────────


def test_steps_ordered_and_passport_locked():
    items, progress = compose_checklist(dependency_graph(), eligibility_eligible(), [])

    assert [it["ord"] for it in items] == [0, 1, 2, 3]
    assert items[0]["title"] == "Obtain police report"

    passport_steps = [it for it in items if it["service"] == "passport_application"]
    assert passport_steps and all(it["status"] == "locked" for it in passport_steps)
    assert all(it["reason"] == "Valid NIC required" for it in passport_steps)
    assert progress == 0


def test_first_unlocked_step_is_active():
    items, _ = compose_checklist(dependency_graph(), eligibility_eligible(), [])
    active = [it for it in items if it["status"] == "active"]
    assert len(active) == 1
    assert active[0]["title"] == "Obtain police report"


def test_accepted_document_completes_step_and_advances_active():
    docs = [{"name": "Police Report", "status": "accepted"}]
    items, progress = compose_checklist(dependency_graph(), eligibility_eligible(), docs)

    police = next(it for it in items if it["title"] == "Obtain police report")
    assert police["status"] == "completed"
    # next pending step becomes the active one
    active = next(it for it in items if it["status"] == "active")
    assert active["title"] == "Apply for duplicate NIC"
    assert progress == 25  # 1 of 4 completed


def test_eligibility_blocked_locks_service_steps():
    elig = {
        "overall": "blocked",
        "services": {
            "duplicate_nic": {
                "verdict": "blocked",
                "blockers": [{"field": "citizenship", "reason": "Requires your citizenship to be sri_lankan."}],
                "missing_facts": [],
            },
            "passport_application": {"verdict": "eligible", "blockers": [], "missing_facts": []},
        },
    }
    items, _ = compose_checklist(dependency_graph(), elig, [])
    nic_steps = [it for it in items if it["service"] == "duplicate_nic"]
    assert all(it["status"] == "locked" for it in nic_steps)
    assert nic_steps[0]["reason"] == "Requires your citizenship to be sri_lankan."


# ── Node wrapper + persistence ────────────────────────────────────────────────


def test_node_skips_persistence_without_case_id():
    state = {
        "dependency_graph": dependency_graph(),
        "eligibility": eligibility_eligible(),
        "documents": [],
        "logs": [],
    }
    result = cl_mod.checklist(state)
    assert result["progress"] == 0
    assert len(result["checklist"]) == 4
    assert result["logs"][-1]["agent"] == "checklist"


def test_persistence_strips_ui_only_keys(monkeypatch):
    captured: dict = {}

    class _FakeDB:
        def close(self):  # noqa: D401 - test stub
            pass

    monkeypatch.setattr("app.db.session.SessionLocal", lambda: _FakeDB())

    def _fake_replace(db, *, case_id, steps):
        captured["case_id"] = case_id
        captured["steps"] = steps

    monkeypatch.setattr(cl_mod, "replace_steps", _fake_replace)

    state = {
        "case_id": str(uuid4()),
        "dependency_graph": dependency_graph(),
        "eligibility": eligibility_eligible(),
        "documents": [],
        "logs": [],
    }
    cl_mod.checklist(state)

    assert captured["steps"], "replace_steps should have been called"
    for row in captured["steps"]:
        assert set(row).issubset(_STEP_COLUMNS)
        assert "service" not in row and "fulfills" not in row
