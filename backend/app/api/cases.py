"""Owner: M1. Case CRUD + list + continue-later."""
from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.auth.jwt import CurrentUser, get_current_user
from app.db.session import get_db
from app.repositories import cases as repo
from app.repositories import steps as steps_repo
from app.schemas.case import CaseCreate, CaseDetail, CaseOut, StepStatusUpdate

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseOut, status_code=201)
def create_case(
    body: CaseCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return repo.create_case(db, user_id=user.id, goal=body.goal, language=body.language)


@router.get("", response_model=list[CaseDetail])
def list_cases(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    # CaseDetail (with steps) so the dashboard can show each case's next step.
    return repo.list_cases(db, user_id=user.id)


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(
    case_id: UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    case = repo.get_case(db, case_id=case_id, user_id=user.id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.delete("/{case_id}", status_code=204)
def delete_case(
    case_id: UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if not repo.delete_case(db, case_id=case_id, user_id=user.id):
        raise HTTPException(status_code=404, detail="Case not found")


@router.patch("/{case_id}/steps/{step_id}", response_model=CaseDetail)
def update_step_status(
    case_id: UUID,
    step_id: UUID,
    body: StepStatusUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Mark a step completed (or undo it); returns the recomputed case."""
    case = repo.get_case(db, case_id=case_id, user_id=user.id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    step = steps_repo.set_step_status(db, case_id=case_id, step_id=step_id, status=body.status)
    if step is None:
        raise HTTPException(status_code=404, detail="Step not found")

    db.refresh(case)
    return case
