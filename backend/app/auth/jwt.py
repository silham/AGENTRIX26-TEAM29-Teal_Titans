"""Owner: M1. Verify the short-lived HS256 JWT minted by NextAuth and expose the
`get_current_user` dependency. Every protected route scopes its queries by `user.id`.
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import settings

bearer = HTTPBearer(auto_error=True)


class CurrentUser(BaseModel):
    id: str
    email: str | None = None
    role: str = "user"


def is_admin_email(email: str | None) -> bool:
    """True when the email is on the ADMIN_EMAILS allowlist."""
    return bool(email) and email.strip().lower() in settings.admin_email_set


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.auth_secret, algorithms=[settings.jwt_algorithm])


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> CurrentUser:
    try:
        payload = decode_token(creds.credentials)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")
    return CurrentUser(
        id=str(user_id),
        email=payload.get("email"),
        role=str(payload.get("role") or "user"),
    )


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Admin gate for the knowledge-base routes.

    BOTH the token claim and the live allowlist must agree. Re-checking the
    allowlist means removing an email from ADMIN_EMAILS revokes access
    immediately, instead of leaving an 8-hour window on already-minted tokens.
    """
    if user.role == "admin" and is_admin_email(user.email):
        return user
    raise HTTPException(status_code=403, detail="Admin privileges required")
