"""API-level i18n: the X-Language contract and the citizen-goal asymmetry.

Two things are being protected here:

* The dashboard must never wait on the translation model — a cold-cache Sinhala
  load has to return inside the client's request timeout.
* A citizen's own words are echoed back verbatim; only machine-composed text is
  translated.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.jwt import CurrentUser, get_current_user
from app.db.models import Base
from app.db.session import get_db
from app.main import app
from app.repositories import cases as case_repo
from app.repositories import steps as steps_repo

USER = CurrentUser(id="citizen-1", email="nimal@example.lk", role="user")


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def _get_db():
        with Session() as session:
            yield session

    # Normalisation is exercised in test_m8_i18n_understand; here it must be
    # inert so these tests stay offline and deterministic.
    monkeypatch.setattr(
        "app.api.cases.normalize_input",
        lambda text: type(
            "A", (), {"english": text, "detected_language": "en", "script": "latin"}
        )(),
    )

    app.dependency_overrides[get_current_user] = lambda: USER
    app.dependency_overrides[get_db] = _get_db
    test_client = TestClient(app)
    test_client.Session = Session
    yield test_client
    app.dependency_overrides.clear()


def _tag_translator(monkeypatch, *, explode: bool = False):
    """Replace translation with tagging (or an explosion, to prove no call)."""
    def _tr(texts, lang, *, cache_only=False):
        if explode:
            raise AssertionError("the model must not be called here")
        return {t: f"[{lang}]{t}" for t in texts}

    monkeypatch.setattr("app.i18n.localize.translate_many", _tr)


def _seed_case(client, goal="I lost my NIC", goal_source="citizen"):
    with client.Session() as db:
        case = case_repo.create_case(
            db, user_id=USER.id, goal=goal, goal_en=goal, goal_source=goal_source
        )
        steps_repo.replace_steps(
            db,
            case_id=case.id,
            steps=[
                {"ord": 0, "title": "Get a police report", "status": "active",
                 "description": "Report the loss at your police station."},
            ],
        )
        return case.id


# ── header contract ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("header", [None, "", "fr", "<script>alert(1)</script>", "SI"])
def test_language_header_is_validated(client, monkeypatch, header):
    """Anything unrecognised falls back to English rather than erroring.

    A malformed header must never be a reason to deny a citizen their plan.
    'SI' is included because case-insensitivity is intended.
    """
    _tag_translator(monkeypatch)
    case_id = _seed_case(client)
    headers = {"X-Language": header} if header is not None else {}

    res = client.get(f"/cases/{case_id}", headers=headers)

    assert res.status_code == 200
    body = res.json()
    if header == "SI":
        assert body["steps"][0]["title"].startswith("[si]")
    else:
        assert body["steps"][0]["title"] == "Get a police report"


def test_vary_header_is_set(client):
    """Without this a shared cache may serve a Sinhala body to an English request."""
    res = client.get("/health")
    assert "X-Language" in res.headers.get("Vary", "")


# ── the list endpoint must never block on the model ─────────────────────────


def test_list_endpoint_never_calls_the_model(client, monkeypatch):
    """Runs the REAL translator against a real cache, with the model rigged to fail.

    Patching `translate_many` would prove nothing — it *is* called, just with
    cache_only. The claim under test is one layer down: no request to Gemini.
    A cold-cache Sinhala dashboard that waited on the model would blow the
    client's request timeout and surface as "is the server running?".
    """
    from app.i18n import translator

    monkeypatch.setattr(translator, "SessionLocal", client.Session)
    monkeypatch.setattr(
        translator,
        "_call_gemini",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("model was called")),
    )
    _seed_case(client)

    res = client.get("/cases", headers={"X-Language": "si"})

    assert res.status_code == 200
    # Untranslated, but present and in English — the intended degradation.
    assert res.json()[0]["steps"][0]["title"] == "Get a police report"


def test_list_endpoint_requests_cache_only(client, monkeypatch):
    seen: list[bool] = []

    def _tr(texts, lang, *, cache_only=False):
        seen.append(cache_only)
        return {t: t for t in texts}

    monkeypatch.setattr("app.i18n.localize.translate_many", _tr)
    _seed_case(client)

    client.get("/cases", headers={"X-Language": "si"})
    assert seen == [True]


# ── the citizen-goal asymmetry ──────────────────────────────────────────────


def test_a_citizens_own_goal_is_never_translated(client, monkeypatch):
    """They typed it. Round-tripping it would hand back words they never wrote."""
    _tag_translator(monkeypatch)
    case_id = _seed_case(client, goal="මට passport එකක් ඕන", goal_source="citizen")

    body = client.get(f"/cases/{case_id}", headers={"X-Language": "si"}).json()

    assert body["goal"] == "මට passport එකක් ඕන"
    assert body["steps"][0]["title"].startswith("[si]"), "but steps still translate"


def test_a_generated_sub_goal_is_translated(client, monkeypatch):
    _tag_translator(monkeypatch)
    case_id = _seed_case(
        client, goal="I need to get my Birth Certificate", goal_source="generated"
    )

    body = client.get(f"/cases/{case_id}", headers={"X-Language": "si"}).json()

    assert body["goal"] == "[si]I need to get my Birth Certificate"


# ── detail fields ───────────────────────────────────────────────────────────


def test_step_description_and_title_are_translated(client, monkeypatch):
    _tag_translator(monkeypatch)
    case_id = _seed_case(client)

    step = client.get(f"/cases/{case_id}", headers={"X-Language": "ta"}).json()["steps"][0]

    assert step["title"] == "[ta]Get a police report"
    assert step["description"] == "[ta]Report the loss at your police station."


def test_machine_keys_in_the_response_are_untouched(client, monkeypatch):
    """`status` and `fulfills` are compared and branched on, never displayed."""
    _tag_translator(monkeypatch)
    case_id = _seed_case(client)

    step = client.get(f"/cases/{case_id}", headers={"X-Language": "si"}).json()["steps"][0]

    assert step["status"] == "active"
    assert step["ord"] == 0


# ── create: normalisation is stored, not substituted ────────────────────────


def test_create_stores_original_and_english_separately(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.cases.normalize_input",
        lambda text: type(
            "A", (), {"english": "I need a passport", "detected_language": "si",
                      "script": "mixed"}
        )(),
    )

    res = client.post("/cases", json={"goal": "මට passport එකක් ඕන", "language": "en"})

    assert res.status_code == 201
    # The DETECTED language is returned, not the picker value — this is what
    # the client uses to auto-switch.
    assert res.json()["language"] == "si"

    with client.Session() as db:
        case = case_repo.get_case(db, case_id=res.json()["id"], user_id=USER.id)
        assert case.goal == "මට passport එකක් ඕන"
        assert case.goal_en == "I need a passport"
        assert case.goal_source == "citizen"


@pytest.mark.parametrize("goal", ["", "ab", "x" * 2001])
def test_goal_length_is_bounded(client, goal):
    """The goal reaches two LLM prompts, so it cannot be unbounded."""
    assert client.post("/cases", json={"goal": goal}).status_code == 422
