"""Owner: M1. Step persistence (M4's checklist node persists computed steps here)."""
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Step


def list_steps(db: Session, *, case_id: UUID) -> list[Step]:
    return list(db.scalars(select(Step).where(Step.case_id == case_id).order_by(Step.ord)))


def replace_steps(db: Session, *, case_id: UUID, steps: list[dict]) -> list[Step]:
    """Replace all steps for a case. `steps` items use Step column names
    (ord, title, description, status, depends_on, source_url, reason)."""
    db.execute(delete(Step).where(Step.case_id == case_id))
    objs = [Step(case_id=case_id, **s) for s in steps]
    db.add_all(objs)
    db.commit()
    return objs
