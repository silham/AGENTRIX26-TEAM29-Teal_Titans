"""M4 tests — reminder node (missing docs, expiry, appointment, inactivity, next action).

Run with:  pytest tests/test_m4_reminder.py -v
"""
from __future__ import annotations

from datetime import date, timedelta

import app.graph.nodes.reminder as rem_mod
from app.graph.nodes.reminder import derive_reminders

_TODAY = date(2026, 6, 20)


def _types(reminders: list[dict]) -> set[str]:
    return {r["type"] for r in reminders}


def test_missing_document_reminder():
    docs = [{"name": "NIC", "status": "missing"}]
    reminders = derive_reminders([], docs, {}, today=_TODAY)
    assert "missing_document" in _types(reminders)
    assert "upload NIC" in reminders[0]["message"]


def test_rejected_document_says_fix():
    docs = [{"name": "Passport Photo", "status": "rejected"}]
    reminders = derive_reminders([], docs, {}, today=_TODAY)
    msg = next(r["message"] for r in reminders if r["type"] == "missing_document")
    assert "fix Passport Photo" in msg


def test_next_action_from_active_step():
    checklist = [{"title": "Obtain police report", "status": "active"}]
    reminders = derive_reminders(checklist, [], {}, today=_TODAY)
    assert "next_action" in _types(reminders)


def test_expiry_within_window_from_facts():
    soon = (_TODAY + timedelta(days=10)).isoformat()
    reminders = derive_reminders([], [], {"license_expiry": soon}, today=_TODAY)
    expiry = [r for r in reminders if r["type"] == "expiry"]
    assert expiry and "10 day" in expiry[0]["message"]


def test_no_expiry_reminder_when_far_off():
    far = (_TODAY + timedelta(days=120)).isoformat()
    reminders = derive_reminders([], [], {"license_expiry": far}, today=_TODAY)
    assert "expiry" not in _types(reminders)


def test_document_expiry_reminder():
    docs = [{"name": "Passport", "status": "accepted", "expires_at": (_TODAY + timedelta(days=5)).isoformat()}]
    reminders = derive_reminders([], docs, {}, today=_TODAY)
    assert "expiry" in _types(reminders)


def test_appointment_reminder():
    appt = (_TODAY + timedelta(days=1)).isoformat()
    reminders = derive_reminders([], [], {"appointment_date": appt}, today=_TODAY)
    assert "appointment" in _types(reminders)


def test_inactivity_reminder():
    checklist = [
        {"title": "Apply for duplicate NIC", "status": "active",
         "updated_at": (_TODAY - timedelta(days=10)).isoformat()}
    ]
    reminders = derive_reminders(checklist, [], {}, today=_TODAY)
    assert "inactivity" in _types(reminders)


def test_node_wraps_and_logs():
    state = {
        "checklist": [{"title": "Obtain police report", "status": "active"}],
        "documents": [{"name": "NIC", "status": "missing"}],
        "facts": {},
        "logs": [],
    }
    result = rem_mod.reminder(state)
    assert isinstance(result["reminders"], list)
    assert result["logs"][-1]["agent"] == "reminder"
