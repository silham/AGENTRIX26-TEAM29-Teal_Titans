"""Owner: M4. Reminder node — appointment / expiry / inactivity / missing-doc nudges.

Derives a list of actionable nudges for the dashboard from the current case state.
Pure and deterministic; safe to run without a DB.

Consumes (from GraphState)
    checklist : list[dict]   (M4) ordered steps with statuses; items may carry an
                             optional "updated_at" / "appointment_at" ISO string
    documents : list[dict]   (M5) [{"name","status",...}]; items may carry "expires_at"
    facts     : dict         optional citizen facts; may carry date strings such as
                             "appointment_date", "license_expiry" (ISO yyyy-mm-dd)

Produces (into GraphState)
    reminders : list[dict]   [{"type","message","severity","due"?}, ...]
        type     : missing_document | next_action | appointment | expiry | inactivity
        severity : info | warning
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from app.graph.nodes.audit import audit
from app.graph.state import GraphState

_EXPIRY_WARN_DAYS = 30
_INACTIVE_DAYS = 7
_NEEDS_ACTION_DOC = {"missing", "rejected", "incomplete"}


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _days_until(d: date, today: date) -> int:
    return (d - today).days


def derive_reminders(
    checklist: list[dict],
    documents: list[dict],
    facts: dict[str, Any],
    *,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Pure reminder derivation (``today`` injectable for tests)."""
    today = today or datetime.now(timezone.utc).date()
    reminders: list[dict[str, Any]] = []

    # 1. Missing / rejected / incomplete documents.
    for doc in documents or []:
        if doc.get("status") in _NEEDS_ACTION_DOC:
            name = doc.get("name", "a required document")
            # Nothing is uploaded any more — the citizen obtains the item and
            # confirms it on the Requirements tab.
            verb = "get" if doc.get("status") == "missing" else "sort out"
            reminders.append(
                {
                    "type": "missing_document",
                    "message": f"You still need to {verb} {name}.",
                    "severity": "warning",
                }
            )

    # 2. Document / fact expiry within the warning window.
    for doc in documents or []:
        exp = _parse_date(doc.get("expires_at"))
        if exp is not None:
            days = _days_until(exp, today)
            if days <= _EXPIRY_WARN_DAYS:
                reminders.append(
                    {
                        "type": "expiry",
                        "message": (
                            f"{doc.get('name', 'A document')} "
                            + (f"expires in {days} day(s)." if days >= 0 else "has expired.")
                        ),
                        "severity": "warning",
                        "due": exp.isoformat(),
                    }
                )
    for field, value in (facts or {}).items():
        if not field.endswith(("_expiry", "_expires", "_expiry_date")):
            continue
        exp = _parse_date(value)
        if exp is not None:
            days = _days_until(exp, today)
            if days <= _EXPIRY_WARN_DAYS:
                label = field.replace("_", " ")
                reminders.append(
                    {
                        "type": "expiry",
                        "message": (
                            f"Your {label} "
                            + (f"is in {days} day(s)." if days >= 0 else "has passed.")
                        ),
                        "severity": "warning",
                        "due": exp.isoformat(),
                    }
                )

    # 3. Upcoming appointments (from facts or step metadata).
    appt = _parse_date((facts or {}).get("appointment_date"))
    if appt is not None and _days_until(appt, today) >= 0:
        reminders.append(
            {
                "type": "appointment",
                "message": f"You have an appointment on {appt.isoformat()}.",
                "severity": "info",
                "due": appt.isoformat(),
            }
        )

    # 4. Inactivity on the active step.
    for item in checklist or []:
        if item.get("status") != "active":
            continue
        last = _parse_date(item.get("updated_at"))
        if last is not None and _days_until(last, today) <= -_INACTIVE_DAYS:
            reminders.append(
                {
                    "type": "inactivity",
                    "message": (
                        f"No progress on \"{item.get('title', 'your current step')}\" "
                        f"for over {_INACTIVE_DAYS} days."
                    ),
                    "severity": "warning",
                }
            )

    # 5. Next best action nudge.
    active = next((it for it in (checklist or []) if it.get("status") == "active"), None)
    if active:
        reminders.append(
            {
                "type": "next_action",
                "message": f"Next step: {active.get('title', '')}".strip(),
                "severity": "info",
            }
        )

    return reminders


def reminder(state: GraphState) -> dict:
    reminders = derive_reminders(
        state.get("checklist", []) or [],
        state.get("documents", []) or [],
        state.get("facts", {}) or {},
    )

    log_update = audit(
        state,
        agent="reminder",
        decision=f"Generated {len(reminders)} reminder(s)",
        confidence=1.0,
    )

    return {"reminders": reminders, **log_update}
