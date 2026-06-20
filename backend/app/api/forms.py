"""Owner: M5. Form-assist endpoints. TODO(M5)."""
from fastapi import APIRouter, Depends

from app.auth.jwt import CurrentUser, get_current_user

router = APIRouter(prefix="/forms", tags=["forms"])


@router.get("/_ping")
def ping(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"ok": True, "owner": "M5"}


# TODO(M5): POST /forms/explain, POST /forms/validate
