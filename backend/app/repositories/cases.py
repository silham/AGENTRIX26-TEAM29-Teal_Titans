"""Owner: M1. Case persistence."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models import Case

# Both endpoints serialise CaseDetail, which touches every one of these. Without
# them each row triggers a separate query per relationship.
_DETAIL_LOADS = (
    selectinload(Case.steps),
    selectinload(Case.documents),
    selectinload(Case.sub_goals),
    joinedload(Case.parent),
)


def _sid(case_id: UUID | str) -> str:
    """Normalise UUID or str to a plain string for SQLite-compatible queries."""
    return str(case_id)


def create_case(
    db: Session,
    *,
    user_id: str,
    goal: str,
    language: str = "en",
    parent_case_id: str | None = None,
    parent_requirement_key: str | None = None,
) -> Case:
    case = Case(
        user_id=user_id,
        goal=goal,
        language=language,
        parent_case_id=parent_case_id,
        parent_requirement_key=parent_requirement_key,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def list_cases(db: Session, *, user_id: str) -> list[Case]:
    return list(
        db.scalars(
            select(Case)
            .options(*_DETAIL_LOADS)
            .where(Case.user_id == user_id)
            .order_by(Case.created_at.desc())
        )
    )


def get_case(db: Session, *, case_id: UUID | str, user_id: str) -> Case | None:
    return db.scalar(
        select(Case)
        .options(*_DETAIL_LOADS)
        .where(Case.id == _sid(case_id), Case.user_id == user_id)
    )


def delete_case(db: Session, *, case_id: UUID | str, user_id: str) -> bool:
    case = db.scalar(select(Case).where(Case.id == _sid(case_id), Case.user_id == user_id))
    if case is None:
        return False
    db.delete(case)
    db.commit()
    return True
