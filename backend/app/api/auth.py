"""Auth endpoints — mint a personalized JWT for demo/hackathon mode.

POST /auth/token  { email, name? }  → { token, user_id, email, name }

For the hackathon any email is accepted as identity (no real password check).
The token is HS256-signed with AUTH_SECRET so FastAPI's get_current_user
dependency accepts it exactly like a NextAuth token.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from jose import jwt
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenRequest(BaseModel):
    email: str
    name: str | None = None


class TokenResponse(BaseModel):
    token: str
    user_id: str
    email: str
    name: str | None = None
    role: str = "user"


@router.post("/token", response_model=TokenResponse)
def mint_token(body: TokenRequest) -> TokenResponse:
    """Return a short-lived JWT scoped to the given email address."""
    from app.auth.jwt import is_admin_email

    email = body.email.lower().strip()
    # Deterministic user_id from email so the same user always gets the same ID
    user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, email))
    role = "admin" if is_admin_email(email) else "user"
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "name": body.name,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=8)).timestamp()),
    }
    token = jwt.encode(payload, settings.auth_secret, algorithm=settings.jwt_algorithm)
    # role is echoed in the body so the frontend can gate the admin nav entry
    # without decoding the JWT client-side.
    return TokenResponse(token=token, user_id=user_id, email=email, name=body.name, role=role)
