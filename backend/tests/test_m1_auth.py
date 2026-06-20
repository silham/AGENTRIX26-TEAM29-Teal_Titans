"""Owner: M1. End-to-end auth: a minted token passes verification, a bad one 401s.
Uses the protected /documents/_ping (auth-only, no DB) so it runs without Postgres."""
from fastapi.testclient import TestClient

from app.auth.mint_token import mint
from app.main import app

client = TestClient(app)


def test_minted_token_passes_auth():
    token = mint("dev-user-001", "dev@helplk.lk", hours=1)
    r = client.get("/documents/_ping", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_invalid_token_rejected():
    r = client.get("/documents/_ping", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


def test_missing_token_rejected():
    r = client.get("/documents/_ping")
    assert r.status_code == 403  # HTTPBearer: no credentials supplied
