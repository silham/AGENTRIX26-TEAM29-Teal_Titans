"""Owner: M6. Admin knowledge API: validation, 202 contract, delete.

The admin gate and the DB session are overridden so this runs without Postgres;
ingestion is stubbed so nothing embeds.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.jwt import CurrentUser, require_admin
from app.config import settings
from app.db.models import Base
from app.db.session import get_db
from app.main import app

ADMIN = CurrentUser(id="admin-1", email="boss@gov.lk", role="admin")


@pytest.fixture
def client(monkeypatch, tmp_path):
    # StaticPool: without it every new connection to `sqlite://` gets its own
    # fresh in-memory database, so the tables created here would be invisible to
    # the request's session.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def _get_db():
        with Session() as session:
            yield session

    queued: list[str] = []
    monkeypatch.setattr(
        "app.api.admin.pipeline.ingest_uploaded_document", lambda doc_id: queued.append(doc_id)
    )
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    app.dependency_overrides[require_admin] = lambda: ADMIN
    app.dependency_overrides[get_db] = _get_db
    test_client = TestClient(app)
    test_client.queued = queued
    yield test_client
    app.dependency_overrides.clear()


def _upload(client, name="guide.txt", body=b"x" * 500, **data):
    return client.post(
        "/admin/knowledge",
        files={"file": (name, body, "text/plain")},
        data=data,
    )


# ── validation ──────────────────────────────────────────────────────────────


def test_unsupported_extension_is_rejected(client):
    r = _upload(client, name="payload.exe")
    assert r.status_code == 415
    assert "Allowed" in r.json()["detail"]


def test_legacy_doc_is_rejected(client):
    assert _upload(client, name="circular.doc").status_code == 415


def test_empty_file_is_rejected(client):
    assert _upload(client, body=b"").status_code == 400


def test_oversized_file_is_rejected_by_the_cap(client, monkeypatch):
    monkeypatch.setattr(settings, "max_knowledge_upload_mb", 1)
    assert _upload(client, body=b"x" * (2 * 1024 * 1024)).status_code == 413


# ── upload contract ─────────────────────────────────────────────────────────


def test_upload_returns_202_pending_and_queues_ingestion(client):
    r = _upload(client, title="Pension Guide", source_url="https://pensions.gov.lk/wop")
    assert r.status_code == 202  # async: a scanned PDF outlives the 15s client timeout
    body = r.json()
    assert body["status"] == "pending"
    assert body["title"] == "Pension Guide"
    assert body["source_url"] == "https://pensions.gov.lk/wop"
    assert body["uploaded_by"] == ADMIN.email
    assert client.queued == [body["id"]]


def test_upload_without_metadata_falls_back_to_the_filename(client):
    body = _upload(client).json()
    assert body["title"] == "guide.txt"
    assert body["source_url"] is None


# ── list / get / delete ─────────────────────────────────────────────────────


def test_uploaded_document_appears_in_the_listing(client):
    doc_id = _upload(client).json()["id"]
    listing = client.get("/admin/knowledge").json()
    assert listing["total"] == 1
    assert [d["id"] for d in listing["documents"]] == [doc_id]


def test_status_filter_narrows_the_listing(client):
    _upload(client)
    assert client.get("/admin/knowledge", params={"status": "ready"}).json()["total"] == 1
    assert client.get("/admin/knowledge", params={"status": "ready"}).json()["documents"] == []


def test_get_unknown_document_is_404(client):
    assert client.get("/admin/knowledge/does-not-exist").status_code == 404


def test_delete_removes_the_document(client):
    doc_id = _upload(client).json()["id"]
    r = client.delete(f"/admin/knowledge/{doc_id}")
    assert r.status_code == 200
    assert r.json()["deleted"] is True
    assert client.get(f"/admin/knowledge/{doc_id}").status_code == 404


def test_reindex_requeues_ingestion(client):
    doc_id = _upload(client).json()["id"]
    client.queued.clear()
    r = client.post(f"/admin/knowledge/{doc_id}/reindex")
    assert r.status_code == 202
    assert r.json()["status"] == "pending"
    assert client.queued == [doc_id]


def test_stats_exposes_retrieval_health(client):
    _upload(client)
    stats = client.get("/admin/knowledge/stats").json()
    assert stats["documents"] == 1
    # The health block is how an operator sees failures search() swallows.
    assert "dialect" in stats["retrieval"]
