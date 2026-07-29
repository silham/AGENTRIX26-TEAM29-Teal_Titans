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


def recompute(db: Session, *, case_id: UUID | str, steps: list[Step] | None = None) -> None:
    """Re-derive lock/active states and case progress. Does NOT commit.

    Deterministic pass over the ordered step list:
      * a dependency-gated step (one persisted with a lock ``reason``) stays
        ``locked`` until every step before it is completed;
      * the first non-completed, non-locked step becomes ``active``;
      * case ``progress`` = completed/total, ``status`` flips to ``completed``
        at 100%, and ``current_step_id`` tracks the active step.

    Note it only ever *demotes* outstanding steps to locked/active/pending —
    completing a later step never back-fills earlier ones as done.

    Callers that mutate several steps must mutate them all first and call this
    once; calling it between mutations would recompute from a half-applied state.
    """
    sid = _sid(case_id)
    if steps is None:
        steps = list_steps(db, case_id=sid)

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
        case.status = "completed" if steps and done == len(steps) else "in_progress"
        active = next((s for s in steps if s.status == "active"), None)
        case.current_step_id = active.id if active else None

    db.flush()


def set_steps_status(
    db: Session, *, case_id: UUID | str, step_ids: set[str], status: str
) -> list[Step]:
    """Set several steps to one status, then recompute once. Does NOT commit."""
    sid = _sid(case_id)
    steps = list_steps(db, case_id=sid)
    targets = [s for s in steps if s.id in step_ids]
    for s in targets:
        s.status = status
    recompute(db, case_id=sid, steps=steps)
    return targets


def set_step_status(
    db: Session, *, case_id: UUID | str, step_id: UUID | str, status: str
) -> Step | None:
    """Mark a step completed (or back to pending) and recompute the case state.

    Returns the updated Step, or None if it doesn't belong to this case.
    """
    sid = _sid(case_id)
    steps = list_steps(db, case_id=sid)
    target = next((s for s in steps if s.id == str(step_id)), None)
    if target is None:
        return None

    target.status = status
    recompute(db, case_id=sid, steps=steps)

    db.commit()
    db.refresh(target)
    return target
