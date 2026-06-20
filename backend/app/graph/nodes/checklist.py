"""Owner: M4. Checklist node — ordered tasks + progress + next best action.

Combines requirements (M3), dependency order/locks (M3) and eligibility (M4) into
a single ordered, status-bearing task list, computes a progress %, marks the one
"next best action", and persists the steps via M1's repositories.steps.

Consumes (from GraphState)
    requirements      : list[str]            (M3) requirement ids across services
    dependency_graph  : dict                 (M3) see SHAPE below
    eligibility       : dict                  (M4) from the eligibility node
    documents         : list[dict]           (M5) [{"name","type","status","issues"}, ...]
    case_id           : str

Produces (into GraphState)
    checklist : list[dict]   ordered items (richer than a Step row; for the UI)
    progress  : int          0–100

dependency_graph SHAPE this node expects from M3 (documented here so M3 can align;
all keys read defensively):
    {
      "order": ["duplicate_nic", "passport_application"],   # service ids, dependency-sorted
      "services": {
        "<service_id>": {
          "name": "Passport Application",
          "blocked": false,
          "reason": "Valid NIC required",        # when blocked
          "depends_on": ["valid_nic"],
          "source_url": "https://...",
          "steps": [
            {"title": "...", "description": "...", "source_url": "...",
             "fulfills": "police_report"}         # optional: requirement id this step satisfies
          ]
        }
      }
    }

Step persistence uses M1's column names only (ord, title, description, status,
depends_on, source_url, reason); UI-only keys (service, fulfills) are stripped.
"""
from __future__ import annotations

from typing import Any

from app.graph.nodes.audit import audit
from app.graph.state import GraphState
from app.repositories.steps import replace_steps

# Columns accepted by repositories.steps.replace_steps (-> Step(**item)).
_STEP_COLUMNS = {"ord", "title", "description", "status", "depends_on", "source_url", "reason"}


def _accepted_requirements(documents: list[dict]) -> set[str]:
    """Requirement keys considered satisfied by an accepted document.

    Matches on document type then name, normalised to snake_case so a doc named
    "Police Report" satisfies a step that ``fulfills`` "police_report"."""
    done: set[str] = set()
    for doc in documents or []:
        if doc.get("status") != "accepted":
            continue
        for key in (doc.get("type"), doc.get("name")):
            if key:
                done.add(str(key).strip().lower().replace(" ", "_"))
    return done


def _service_order(dependency_graph: dict) -> list[str]:
    order = dependency_graph.get("order")
    if order:
        return list(order)
    return list((dependency_graph.get("services") or {}).keys())


def compose_checklist(
    dependency_graph: dict,
    eligibility: dict,
    documents: list[dict],
) -> tuple[list[dict[str, Any]], int]:
    """Pure composition. Returns (ordered_items, progress_percent)."""
    services = (dependency_graph or {}).get("services") or {}
    elig_services = (eligibility or {}).get("services") or {}
    satisfied = _accepted_requirements(documents)

    items: list[dict[str, Any]] = []
    ord_counter = 0
    first_pending_idx: int | None = None

    for sid in _service_order(dependency_graph or {}):
        svc = services.get(sid, {}) or {}
        # A service is locked by a dependency OR by an eligibility "blocked" verdict.
        dep_blocked = bool(svc.get("blocked"))
        elig_verdict = (elig_services.get(sid) or {}).get("verdict")
        elig_blocked = elig_verdict == "blocked"
        locked = dep_blocked or elig_blocked

        if dep_blocked:
            lock_reason = svc.get("reason") or "Blocked by a prerequisite step."
        elif elig_blocked:
            blockers = (elig_services.get(sid) or {}).get("blockers") or []
            lock_reason = blockers[0]["reason"] if blockers else "Not eligible for this service."
        else:
            lock_reason = None

        for step in svc.get("steps", []) or []:
            fulfills = step.get("fulfills")
            if locked:
                status = "locked"
            elif fulfills and str(fulfills).lower() in satisfied:
                status = "completed"
            else:
                status = "pending"
                if first_pending_idx is None:
                    first_pending_idx = len(items)

            items.append(
                {
                    "ord": ord_counter,
                    "title": step.get("title", ""),
                    "description": step.get("description"),
                    "status": status,
                    "depends_on": svc.get("depends_on", []) or [],
                    "source_url": step.get("source_url") or svc.get("source_url"),
                    "reason": lock_reason if status == "locked" else None,
                    # UI-only metadata (stripped before persistence):
                    "service": sid,
                    "fulfills": fulfills,
                }
            )
            ord_counter += 1

    # The single "next best action": first pending step becomes active.
    if first_pending_idx is not None:
        items[first_pending_idx]["status"] = "active"

    total = len(items)
    completed = sum(1 for it in items if it["status"] == "completed")
    progress = round(completed / total * 100) if total else 0

    return items, progress


def _persist(case_id: str, items: list[dict]) -> None:
    """Persist steps via M1's repo. Best-effort: skipped if no DB (unit tests)."""
    if not case_id:
        return
    from uuid import UUID

    from app.db.session import SessionLocal

    rows = [{k: v for k, v in it.items() if k in _STEP_COLUMNS} for it in items]
    db = SessionLocal()
    try:
        replace_steps(db, case_id=UUID(str(case_id)), steps=rows)
    finally:
        db.close()


def checklist(state: GraphState) -> dict:
    items, progress = compose_checklist(
        state.get("dependency_graph", {}) or {},
        state.get("eligibility", {}) or {},
        state.get("documents", []) or [],
    )

    try:
        _persist(state.get("case_id", ""), items)
    except Exception:
        # Composition is the source of truth for the stream; persistence is best-effort.
        pass

    next_action = next((it["title"] for it in items if it["status"] == "active"), None)
    log_update = audit(
        state,
        agent="checklist",
        decision=f"Built {len(items)} steps, progress {progress}%",
        reason=f"Next best action: {next_action}" if next_action else "No actionable step",
        confidence=1.0,
    )

    return {"checklist": items, "progress": progress, **log_update}
