"""Owner: M1. Case CRUD + list + continue-later."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.jwt import CurrentUser, get_current_user
from app.db.session import get_db
from app.repositories import cases as repo
from app.schemas.case import CaseCreate, CaseDetail, CaseOut

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseOut, status_code=201)
def create_case(
    body: CaseCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return repo.create_case(db, user_id=user.id, goal=body.goal, language=body.language)


@router.get("", response_model=list[CaseOut])
def list_cases(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
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
