"""Owner: M1. Smoke tests — app boots and auth is enforced (no DB needed)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_cases_requires_auth():
    # No bearer token → rejected by HTTPBearer.
    r = client.get("/cases")
    assert r.status_code in (401, 403)
