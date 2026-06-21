"""Owner: M1. Step persistence (M4's checklist node persists computed steps here)."""
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Step


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
