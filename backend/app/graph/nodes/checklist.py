"""Owner: M4. Checklist node — ordered tasks + progress + next best action.

Combines dependency order/locks (M3) and eligibility (M4) with the per-service
steps from the rules layer (M3) into a single ordered, status-bearing task list,
computes a progress %, marks the one "next best action", and persists the steps
via M1's repositories.steps.

Consumes (from GraphState)
    dependency_graph  : dict          (M3) see SHAPE below
    eligibility       : dict          (M4) from the eligibility node
    documents         : list[dict]    (M5) [{"name","type","status","issues"}, ...]
    case_id           : str

Produces (into GraphState)
    checklist : list[dict]   ordered items (richer than a Step row; for the UI)
    progress  : int          0–100

dependency_graph SHAPE (produced by M3's dependency node):
    {
      "services": {
        "<service_id>": {
          "name": str,
          "depends_on": [service_id, ...],
          "status": "ready" | "locked",
          "reason": str | None,            # when locked
          "blocked_by": [service_id, ...],
        }, ...
      },
      "order": [service_id, ...],          # prerequisites first
      "locked": [service_id, ...],
    }
The per-service *steps* are NOT in the dependency graph — they come from
rules.steps(service) (each: title, description, source_url).

Step persistence uses M1's column names only (ord, title, description, status,
depends_on, source_url, reason); UI-only keys (service, fulfills) are stripped.
"""
from __future__ import annotations

from typing import Any

from app.graph.nodes.audit import audit
from app.graph.state import GraphState
from app.rag import rules
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


def _is_locked(svc: dict, elig_service: dict) -> tuple[bool, str | None]:
    """Lock a service if M3 locked it (status) OR eligibility blocked it."""
    dep_locked = svc.get("status") == "locked" or bool(svc.get("blocked"))
    if dep_locked:
        return True, svc.get("reason") or "Blocked by a prerequisite step."
    if (elig_service or {}).get("verdict") == "blocked":
        blockers = (elig_service or {}).get("blockers") or []
        return True, blockers[0]["reason"] if blockers else "Not eligible for this service."
    return False, None


def compose_checklist(
    dependency_graph: dict,
    eligibility: dict,
    documents: list[dict],
    steps_by_service: dict[str, list[dict]],
) -> tuple[list[dict[str, Any]], int]:
    """Pure composition. Returns (ordered_items, progress_percent).

    ``steps_by_service`` maps service_id -> ordered step dicts (from rules.steps),
    kept as a parameter so this stays pure and unit-testable without the rules layer.
    """
    services = (dependency_graph or {}).get("services") or {}
    elig_services = (eligibility or {}).get("services") or {}
    satisfied = _accepted_requirements(documents)

    items: list[dict[str, Any]] = []
    ord_counter = 0
    first_pending_idx: int | None = None

    for sid in _service_order(dependency_graph or {}):
        svc = services.get(sid, {}) or {}
        locked, lock_reason = _is_locked(svc, elig_services.get(sid) or {})

        for step in steps_by_service.get(sid, []) or []:
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
                    "source_url": step.get("source_url") or rules_source(sid),
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


def rules_source(service: str) -> str | None:
    """Service-level source URL fallback (wrapped so tests can monkeypatch)."""
    try:
        return rules.source_url(service)
    except Exception:
        return None


def _persist(case_id: str, items: list[dict], progress: int) -> None:
    """Persist steps and update Case.progress. Logs errors instead of silently failing."""
    if not case_id:
        return
    import sys
    from uuid import UUID

    from sqlalchemy import update

    from app.db.models import Case
    from app.db.session import SessionLocal

    rows = [{k: v for k, v in it.items() if k in _STEP_COLUMNS} for it in items]
    if not rows:
        # Nothing to write — don't wipe previously saved steps from an earlier run.
        return
    db = SessionLocal()
    try:
        replace_steps(db, case_id=UUID(str(case_id)), steps=rows)
        # Also write progress back to the Case row so the dashboard card is accurate.
        db.execute(
            update(Case)
            .where(Case.id == str(case_id))
            .values(progress=progress)
        )
        db.commit()
    except Exception as exc:
        print(f"[checklist] _persist failed for case {case_id}: {exc!r}", file=sys.stderr)
        raise
    finally:
        db.close()


def checklist(state: GraphState) -> dict:
    import sys
    dep_graph = state.get("dependency_graph", {}) or {}
    order = _service_order(dep_graph)
    custom = state.get("custom_steps") or []

    print(
        f"[checklist] services={order}  custom_steps={len(custom)}"
        f"  goal={state.get('goal','')[:60]}",
        file=sys.stderr,
    )

    steps_by_service = {
        sid: (custom if sid == "custom_procedure" else rules.steps(sid))
        for sid in order
    }

    items, progress = compose_checklist(
        dep_graph,
        state.get("eligibility", {}) or {},
        state.get("documents", []) or [],
        steps_by_service,
    )

    print(f"[checklist] composed {len(items)} items  progress={progress}%", file=sys.stderr)

    try:
        _persist(state.get("case_id", ""), items, progress)
    except Exception:
        # Steps are still returned in the SSE stream even if DB write fails.
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
