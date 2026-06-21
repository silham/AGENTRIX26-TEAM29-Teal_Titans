"""Owner: M1. Case persistence."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Case


def _sid(case_id: UUID | str) -> str:
    """Normalise UUID or str to a plain string for SQLite-compatible queries."""
    return str(case_id)


def create_case(db: Session, *, user_id: str, goal: str, language: str = "en") -> Case:
    case = Case(user_id=user_id, goal=goal, language=language)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def list_cases(db: Session, *, user_id: str) -> list[Case]:
    return list(
        db.scalars(select(Case).where(Case.user_id == user_id).order_by(Case.created_at.desc()))
    )


def get_case(db: Session, *, case_id: UUID | str, user_id: str) -> Case | None:
    return db.scalar(
        select(Case)
        .options(selectinload(Case.steps))
        .where(Case.id == _sid(case_id), Case.user_id == user_id)
    )


def delete_case(db: Session, *, case_id: UUID | str, user_id: str) -> bool:
    case = db.scalar(select(Case).where(Case.id == _sid(case_id), Case.user_id == user_id))
    if case is None:
        return False
    db.delete(case)
    db.commit()
    return True
