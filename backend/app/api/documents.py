"""Owner: M5. Document upload / verify / delete. TODO(M5)."""
from fastapi import APIRouter, Depends

from app.auth.jwt import CurrentUser, get_current_user

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/_ping")
def ping(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"ok": True, "owner": "M5"}


# TODO(M5): POST /documents (upload + verify), GET /documents/{id}, DELETE /documents/{id}
