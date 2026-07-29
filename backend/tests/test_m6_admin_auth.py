"""Owner: M6. Admin gate: ADMIN_EMAILS allowlist -> role claim -> require_admin.

No DB, no API keys — the allowlist is a plain property on settings so
monkeypatching it needs no cache busting.
"""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth.jwt import CurrentUser, is_admin_email, require_admin
from app.config import settings
from app.main import app

client = TestClient(app)


@pytest.fixture
def allowlist(monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", "boss@gov.lk, second@gov.lk")


def test_admin_email_matching_is_case_and_space_insensitive(allowlist):
    assert is_admin_email("boss@gov.lk")
    assert is_admin_email("  BOSS@GOV.LK  ")
    assert is_admin_email("second@gov.lk")
    assert not is_admin_email("nobody@example.com")
    assert not is_admin_email(None)


def test_empty_allowlist_grants_nobody(monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", "")
    assert not is_admin_email("boss@gov.lk")


def test_mint_token_sets_role_for_allowlisted_email_only(allowlist):
    admin = client.post("/auth/token", json={"email": "boss@gov.lk"}).json()
    citizen = client.post("/auth/token", json={"email": "nobody@example.com"}).json()
    assert admin["role"] == "admin"
    assert citizen["role"] == "user"


def test_require_admin_accepts_admin(allowlist):
    user = CurrentUser(id="u1", email="boss@gov.lk", role="admin")
    assert require_admin(user) is user


def test_require_admin_rejects_plain_user(allowlist):
    with pytest.raises(HTTPException) as exc:
        require_admin(CurrentUser(id="u1", email="nobody@example.com", role="user"))
    assert exc.value.status_code == 403


def test_require_admin_rejects_revoked_admin_holding_a_valid_token(monkeypatch):
    """A token minted while allowlisted must stop working once the email is
    removed from ADMIN_EMAILS — that is the point of re-checking the allowlist
    rather than trusting the claim alone."""
    monkeypatch.setattr(settings, "admin_emails", "")
    with pytest.raises(HTTPException) as exc:
        require_admin(CurrentUser(id="u1", email="boss@gov.lk", role="admin"))
    assert exc.value.status_code == 403


def test_admin_routes_are_gated_end_to_end(allowlist):
    admin_token = client.post("/auth/token", json={"email": "boss@gov.lk"}).json()["token"]
    citizen_token = client.post("/auth/token", json={"email": "nobody@example.com"}).json()["token"]

    assert client.get("/admin/knowledge").status_code == 403  # no credentials
    assert (
        client.get("/admin/knowledge", headers={"Authorization": f"Bearer {citizen_token}"}).status_code
        == 403
    )
    # The admin path needs a DB, so assert only that it is not rejected by the gate.
    assert (
        client.get("/admin/knowledge", headers={"Authorization": f"Bearer {admin_token}"}).status_code
        != 403
    )
