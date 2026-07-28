"""Step persistence (the checklist node persists computed steps here)."""
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Case, Step


def _sid(case_id: UUID | str) -> str:
    return str(case_id)


def list_steps(db: Session, *, case_id: UUID | str) -> list[Step]:
    return list(db.scalars(select(Step).where(Step.case_id == _sid(case_id)).order_by(Step.ord)))


def replace_steps(db: Session, *, case_id: UUID | str, steps: list[dict]) -> list[Step]:
    """Replace all steps for a case atomically."""
    sid = _sid(case_id)
    db.execute(delete(Step).where(Step.case_id == sid))
    objs = [Step(case_id=sid, **s) for s in steps]
    db.add_all(objs)
    db.commit()
    return objs


def set_step_status(
    db: Session, *, case_id: UUID | str, step_id: UUID | str, status: str
) -> Step | None:
    """Mark a step completed (or back to pending) and recompute the case state.

    Deterministic recompute over the ordered step list:
      * a dependency-gated step (one persisted with a lock ``reason``) stays
        ``locked`` until every step before it is completed;
      * the first non-completed, non-locked step becomes ``active``;
      * case ``progress`` = completed/total, ``status`` flips to ``completed``
        at 100%, and ``current_step_id`` tracks the active step.

    Returns the updated Step, or None if it doesn't belong to this case.
    """
    sid = _sid(case_id)
    steps = list_steps(db, case_id=sid)
    target = next((s for s in steps if s.id == str(step_id)), None)
    if target is None:
        return None

    target.status = status

    # Recompute lock/active states in order. "skipped" counts as satisfied.
    all_prior_done = True
    active_assigned = False
    for s in sorted(steps, key=lambda s: s.ord):
        if s.status in ("completed", "skipped"):
            continue
        gated = bool(s.reason)
        if gated and not all_prior_done:
            s.status = "locked"
        elif not active_assigned:
            s.status = "active"
            active_assigned = True
        else:
            s.status = "pending"
        all_prior_done = False

    done = sum(1 for s in steps if s.status in ("completed", "skipped"))
    case = db.get(Case, sid)
    if case is not None:
        case.progress = round(done * 100 / len(steps)) if steps else 0
        case.status = "completed" if done == len(steps) else "in_progress"
        active = next((s for s in steps if s.status == "active"), None)
        case.current_step_id = active.id if active else None

    db.commit()
    db.refresh(target)
    return target
