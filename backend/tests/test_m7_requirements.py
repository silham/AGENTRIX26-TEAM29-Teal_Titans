"""Owner: M7. Requirements tab — "I have it", undo, and "How to get it?" sub-goals.

No Postgres and no API keys: in-memory SQLite with StaticPool plus dependency
overrides, the same fixture shape as test_m6_admin_api.py.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.jwt import CurrentUser, get_current_user
from app.db.models import Base, Case, Document, Step
from app.db.session import get_db
from app.main import app
from app.repositories import subgoals as subgoal_repo

USER = CurrentUser(id="user-1", email="citizen@example.lk", role="user")
OTHER = CurrentUser(id="user-2", email="other@example.lk", role="user")

TITLES = ["Get police report", "Prepare birth certificate", "Prepare your NIC", "Submit"]


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        yield session


@pytest.fixture
def client(db_session):
    def _get_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user] = lambda: USER
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_case(db, *, user_id=USER.id, goal="Apply for a passport", fulfills_at=2,
              key="valid_nic", n_steps=4, **case_kw):
    """A case with `n_steps` ordered steps; the one at `fulfills_at` obtains `key`."""
    case = Case(user_id=user_id, goal=goal, **case_kw)
    db.add(case)
    db.flush()
    for i in range(n_steps):
        db.add(Step(
            case_id=case.id, ord=i, title=TITLES[i % len(TITLES)],
            status="active" if i == 0 else "pending",
            fulfills=key if i == fulfills_at else None,
        ))
    db.add(Document(case_id=case.id, name="National Identity Card (NIC)", type=key,
                    status="missing"))
    db.commit()
    return case


def steps_of(db, case):
    return sorted(case.steps, key=lambda s: s.ord)


def requirement_of(db, case):
    return case.documents[0]


# ── "I have it" — the user's explicit constraint ────────────────────────────


def test_confirming_requirement_completes_only_the_fulfilling_step(client, db_session):
    case = make_case(db_session, fulfills_at=2)
    doc = requirement_of(db_session, case)

    r = client.patch(f"/cases/{case.id}/requirements/{doc.id}", json={"status": "confirmed"})
    assert r.status_code == 200

    db_session.refresh(case)
    steps = steps_of(db_session, case)
    assert steps[2].status == "completed"
    # The whole point: obtaining item #3 says nothing about steps 1 and 2.
    assert steps[0].status != "completed"
    assert steps[1].status != "completed"
    assert steps[3].status != "completed"
    assert case.progress == 25


def test_earlier_steps_remain_actionable(client, db_session):
    case = make_case(db_session, fulfills_at=2)
    doc = requirement_of(db_session, case)
    client.patch(f"/cases/{case.id}/requirements/{doc.id}", json={"status": "confirmed"})

    db_session.refresh(case)
    steps = steps_of(db_session, case)
    assert steps[0].status == "active"
    assert steps[1].status == "pending"
    assert steps[3].status == "pending"
    assert case.current_step_id == steps[0].id


def test_requirement_status_is_confirmed_not_accepted(client, db_session):
    """'accepted' would claim a verification that never happened."""
    case = make_case(db_session)
    doc = requirement_of(db_session, case)
    body = client.patch(
        f"/cases/{case.id}/requirements/{doc.id}", json={"status": "confirmed"}
    ).json()
    assert [d["status"] for d in body["documents"]] == ["confirmed"]


def test_undo_reverts_step_and_progress(client, db_session):
    case = make_case(db_session, fulfills_at=2)
    doc = requirement_of(db_session, case)
    client.patch(f"/cases/{case.id}/requirements/{doc.id}", json={"status": "confirmed"})
    client.patch(f"/cases/{case.id}/requirements/{doc.id}", json={"status": "missing"})

    db_session.refresh(case)
    steps = steps_of(db_session, case)
    assert requirement_of(db_session, case).status == "missing"
    assert steps[2].status == "pending"
    assert steps[0].status == "active"
    assert case.progress == 0


def test_confirm_is_idempotent(client, db_session):
    case = make_case(db_session, fulfills_at=2)
    doc = requirement_of(db_session, case)
    first = client.patch(
        f"/cases/{case.id}/requirements/{doc.id}", json={"status": "confirmed"}
    ).json()
    second = client.patch(
        f"/cases/{case.id}/requirements/{doc.id}", json={"status": "confirmed"}
    ).json()
    assert first["progress"] == second["progress"]
    assert [s["status"] for s in first["steps"]] == [s["status"] for s in second["steps"]]


def test_all_steps_sharing_a_requirement_key_complete(client, db_session):
    case = make_case(db_session, fulfills_at=2)
    # A second step obtaining the same item, after the existing four (ord 0-3).
    db_session.add(Step(case_id=case.id, ord=4, title="Photocopy the NIC",
                        status="pending", fulfills="valid_nic"))
    db_session.commit()
    doc = requirement_of(db_session, case)

    client.patch(f"/cases/{case.id}/requirements/{doc.id}", json={"status": "confirmed"})
    db_session.refresh(case)
    steps = steps_of(db_session, case)
    assert steps[2].status == "completed"
    assert steps[4].status == "completed"
    assert steps[0].status == "active"
    assert steps[1].status == "pending"


def test_confirm_with_no_matching_step_is_a_no_op_on_steps(client, db_session):
    """Custom LLM plans carry no `fulfills` keys — that must not 500."""
    case = make_case(db_session, fulfills_at=99)  # no step carries the key
    doc = requirement_of(db_session, case)

    r = client.patch(f"/cases/{case.id}/requirements/{doc.id}", json={"status": "confirmed"})
    assert r.status_code == 200
    db_session.refresh(case)
    assert requirement_of(db_session, case).status == "confirmed"
    assert not any(s.status == "completed" for s in case.steps)


def test_requirement_from_another_case_404s(client, db_session):
    case_a = make_case(db_session)
    case_b = make_case(db_session, goal="Renew licence")
    foreign = requirement_of(db_session, case_b)
    r = client.patch(
        f"/cases/{case_a.id}/requirements/{foreign.id}", json={"status": "confirmed"}
    )
    assert r.status_code == 404


def test_case_of_another_user_404s(client, db_session):
    case = make_case(db_session, user_id=OTHER.id)
    doc = requirement_of(db_session, case)
    r = client.patch(f"/cases/{case.id}/requirements/{doc.id}", json={"status": "confirmed"})
    assert r.status_code == 404


def test_invalid_status_is_rejected(client, db_session):
    case = make_case(db_session)
    doc = requirement_of(db_session, case)
    r = client.patch(f"/cases/{case.id}/requirements/{doc.id}", json={"status": "accepted"})
    assert r.status_code == 422


# ── "How to get it?" sub-goals ──────────────────────────────────────────────


def test_sub_goal_records_parent_link(client, db_session):
    case = make_case(db_session)
    doc = requirement_of(db_session, case)

    r = client.post(f"/cases/{case.id}/requirements/{doc.id}/sub-goal")
    assert r.status_code == 201
    body = r.json()
    assert body["parent"]["id"] == str(case.id)
    # valid_nic maps to a real modelled service, so the goal names it.
    assert "National Identity Card" in body["goal"]

    sub = db_session.get(Case, body["id"])
    assert sub.parent_case_id == case.id
    assert sub.parent_requirement_key == "valid_nic"


def test_sub_goal_is_listed_on_the_parent(client, db_session):
    case = make_case(db_session)
    doc = requirement_of(db_session, case)
    sub_id = client.post(f"/cases/{case.id}/requirements/{doc.id}/sub-goal").json()["id"]

    parent = client.get(f"/cases/{case.id}").json()
    assert [g["id"] for g in parent["sub_goals"]] == [sub_id]
    assert parent["sub_goals"][0]["parent_requirement_key"] == "valid_nic"


def test_sub_goal_is_reused_on_a_second_click(client, db_session):
    case = make_case(db_session)
    doc = requirement_of(db_session, case)
    first = client.post(f"/cases/{case.id}/requirements/{doc.id}/sub-goal")
    second = client.post(f"/cases/{case.id}/requirements/{doc.id}/sub-goal")

    assert first.status_code == 201
    assert second.status_code == 200  # reused, not duplicated
    assert first.json()["id"] == second.json()["id"]
    assert db_session.query(Case).count() == 2


def test_unmodelled_requirement_falls_back_to_its_display_name(client, db_session):
    case = make_case(db_session, key="chassis_number")
    doc = case.documents[0]
    doc.name = "Chassis Number"
    db_session.commit()

    body = client.post(f"/cases/{case.id}/requirements/{doc.id}/sub-goal").json()
    assert "Chassis Number" in body["goal"]


def test_sub_goal_creation_rejects_an_over_deep_chain(client, db_session):
    # MAX_CASCADE_DEPTH + 1 cases, so the deepest one already has
    # MAX_CASCADE_DEPTH ancestors and cannot take another level.
    parent_id = None
    for i in range(subgoal_repo.MAX_CASCADE_DEPTH + 1):
        case = make_case(db_session, goal=f"level {i}", parent_case_id=parent_id,
                         parent_requirement_key="valid_nic" if parent_id else None)
        parent_id = case.id
    doc = requirement_of(db_session, case)

    r = client.post(f"/cases/{case.id}/requirements/{doc.id}/sub-goal")
    assert r.status_code == 409


# ── Completion cascade ──────────────────────────────────────────────────────


def _complete_all_steps(client, case):
    for step in sorted(case.steps, key=lambda s: s.ord):
        client.patch(f"/cases/{case.id}/steps/{step.id}", json={"status": "completed"})


def test_completing_sub_goal_confirms_parent_requirement_and_step(client, db_session):
    parent = make_case(db_session, fulfills_at=2)
    doc = requirement_of(db_session, parent)
    sub_id = client.post(f"/cases/{parent.id}/requirements/{doc.id}/sub-goal").json()["id"]
    sub = db_session.get(Case, sub_id)
    db_session.add(Step(case_id=sub.id, ord=0, title="Do the thing", status="active"))
    db_session.commit()

    _complete_all_steps(client, sub)

    db_session.refresh(parent)
    steps = steps_of(db_session, parent)
    assert requirement_of(db_session, parent).status == "confirmed"
    assert steps[2].status == "completed"
    # Same constraint as the manual path: earlier steps are untouched.
    assert steps[0].status == "active"
    assert steps[1].status == "pending"


def test_cascade_reaches_the_grandparent(client, db_session):
    grandparent = make_case(db_session, goal="Passport", fulfills_at=2)
    gp_doc = requirement_of(db_session, grandparent)
    parent_id = client.post(
        f"/cases/{grandparent.id}/requirements/{gp_doc.id}/sub-goal"
    ).json()["id"]

    parent = db_session.get(Case, parent_id)
    db_session.add(Step(case_id=parent.id, ord=0, title="Get police report",
                        status="active", fulfills="police_report"))
    db_session.add(Document(case_id=parent.id, name="Police Report",
                            type="police_report", status="missing"))
    db_session.commit()
    p_doc = parent.documents[0]

    child_id = client.post(
        f"/cases/{parent.id}/requirements/{p_doc.id}/sub-goal"
    ).json()["id"]
    child = db_session.get(Case, child_id)
    db_session.add(Step(case_id=child.id, ord=0, title="Visit the station", status="active"))
    db_session.commit()

    _complete_all_steps(client, child)

    db_session.refresh(parent)
    db_session.refresh(grandparent)
    assert parent.documents[0].status == "confirmed"
    assert parent.status == "completed"
    assert requirement_of(db_session, grandparent).status == "confirmed"


def test_incomplete_sub_goal_does_not_confirm_anything(client, db_session):
    parent = make_case(db_session, fulfills_at=2)
    doc = requirement_of(db_session, parent)
    sub_id = client.post(f"/cases/{parent.id}/requirements/{doc.id}/sub-goal").json()["id"]
    sub = db_session.get(Case, sub_id)
    db_session.add(Step(case_id=sub.id, ord=0, title="One", status="active"))
    db_session.add(Step(case_id=sub.id, ord=1, title="Two", status="pending"))
    db_session.commit()

    first = sorted(sub.steps, key=lambda s: s.ord)[0]
    client.patch(f"/cases/{sub.id}/steps/{first.id}", json={"status": "completed"})

    db_session.refresh(parent)
    assert requirement_of(db_session, parent).status == "missing"


def test_empty_sub_goal_does_not_confirm_the_parent(client, db_session):
    """A freshly spawned plan has no steps yet; 0 of 0 must not read as done."""
    parent = make_case(db_session)
    doc = requirement_of(db_session, parent)
    client.post(f"/cases/{parent.id}/requirements/{doc.id}/sub-goal")

    db_session.refresh(parent)
    assert requirement_of(db_session, parent).status == "missing"


def test_cycle_terminates(client, db_session):
    """Hand-linked A<->B (bypassing the creation guard) must not recurse forever."""
    a = make_case(db_session, goal="A", n_steps=1, fulfills_at=0)
    b = make_case(db_session, goal="B", n_steps=1, fulfills_at=0)
    a.parent_case_id, a.parent_requirement_key = b.id, "valid_nic"
    b.parent_case_id, b.parent_requirement_key = a.id, "valid_nic"
    a.status = b.status = "completed"
    db_session.commit()

    touched = subgoal_repo.propagate_completion(db_session, case_id=a.id)
    assert len(touched) <= subgoal_repo.MAX_CASCADE_DEPTH


def test_cascade_skips_a_parent_owned_by_another_user(client, db_session):
    parent = make_case(db_session, user_id=OTHER.id, fulfills_at=2)
    sub = make_case(db_session, goal="Sub", n_steps=1, fulfills_at=0,
                    parent_case_id=parent.id, parent_requirement_key="valid_nic")
    sub.status = "completed"
    db_session.commit()

    assert subgoal_repo.propagate_completion(db_session, case_id=sub.id) == []
    assert requirement_of(db_session, parent).status == "missing"


def test_deleting_a_parent_leaves_the_sub_goal_alive(client, db_session):
    parent = make_case(db_session)
    doc = requirement_of(db_session, parent)
    sub_id = client.post(f"/cases/{parent.id}/requirements/{doc.id}/sub-goal").json()["id"]

    assert client.delete(f"/cases/{parent.id}").status_code == 204
    survivor = client.get(f"/cases/{sub_id}")
    assert survivor.status_code == 200
    assert survivor.json()["parent"] is None
