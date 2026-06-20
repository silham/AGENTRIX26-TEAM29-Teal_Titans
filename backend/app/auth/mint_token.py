"""Owner: M1. DEV-ONLY: mint a NextAuth-compatible HS256 JWT for local testing.

Signed with the same AUTH_SECRET the backend verifies with, so a minted token is
accepted exactly like one from NextAuth — lets the team call protected routes
before the frontend exists.

    python -m app.auth.mint_token                      # default dev user, 24h
    python -m app.auth.mint_token alice --email a@b.lk --hours 8

Prints the raw token and a ready-to-paste Authorization header.
"""
import argparse
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import settings


def mint(user_id: str = "dev-user-001", email: str | None = None, hours: int = 24) -> str:
    now = datetime.now(timezone.utc)
    payload: dict = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=hours)).timestamp()),
    }
    if email:
        payload["email"] = email
    return jwt.encode(payload, settings.auth_secret, algorithm=settings.jwt_algorithm)


def main() -> None:
    p = argparse.ArgumentParser(description="Mint a dev JWT for HelpLK AI local testing.")
    p.add_argument("user_id", nargs="?", default="dev-user-001")
    p.add_argument("--email", default="dev@helplk.lk")
    p.add_argument("--hours", type=int, default=24)
    args = p.parse_args()

    token = mint(args.user_id, args.email, args.hours)
    print(token)
    print()
    print(f"Authorization: Bearer {token}")


if __name__ == "__main__":
    main()
