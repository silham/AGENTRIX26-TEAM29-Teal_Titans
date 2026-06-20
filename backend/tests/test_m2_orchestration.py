"""M2 tests — agent orchestration (planner, builder, runner, SSE schema).

Run with:  pytest tests/test_m2_orchestration.py -v

These tests use monkeypatching so they work WITHOUT a real Groq key or Postgres
connection.  The external calls (Groq, LangGraph checkpointer) are stubbed.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock


# ── Helpers ───────────────────────────────────────────────────────────────────

_PLANNER_RESPONSE = json.dumps(
    {
        "detected_services": ["duplicate_nic", "passport_application"],
        "intent": {
            "primary_goal": "apply for passport after losing NIC",
            "urgency": "high",
            "has_blocking_issues": True,
            "blocking_issues": ["NIC is lost"],
        },
    }
)

_LICENCE_RESPONSE = json.dumps(
    {
        "detected_services": ["driving_license_renewal"],
        "intent": {
            "primary_goal": "renew driving licence",
            "urgency": "medium",
            "has_blocking_issues": False,
            "blocking_issues": [],
        },
    }
)


# ── RunEvent / SSE schema ─────────────────────────────────────────────────────


def test_run_event_to_sse_format():
    from app.schemas.run import RunEvent

    evt = RunEvent(agent="planner", status="started")
    sse = evt.to_sse()
    assert sse.startswith("data: ")
    assert sse.endswith("\n\n")


def test_run_event_payload_round_trips():
    from app.schemas.run import RunEvent

    evt = RunEvent(agent="knowledge", status="completed", payload={"requirements": ["NIC"]})
    sse = evt.to_sse()
    parsed = json.loads(sse.removeprefix("data: ").strip())
    assert parsed["payload"]["requirements"] == ["NIC"]


def test_run_event_error_shape():
    from app.schemas.run import RunEvent

    evt = RunEvent(agent="system", status="error", message="something broke")
    parsed = json.loads(evt.to_sse().removeprefix("data: ").strip())
    assert parsed["status"] == "error"
    assert parsed["message"] == "something broke"


# ── Planner node ──────────────────────────────────────────────────────────────


def test_planner_detects_dual_service(monkeypatch):
    import app.llm.groq_client as gc

    monkeypatch.setattr(gc, "chat", lambda msgs, **kw: _PLANNER_RESPONSE)

    from app.graph.nodes.planner import planner

    state = {"goal": "I lost my NIC and need a passport", "case_id": "c1", "user_id": "u1", "language": "en"}
    result = planner(state)

    assert "duplicate_nic" in result["detected_services"]
    assert "passport_application" in result["detected_services"]
    assert result["intent"]["has_blocking_issues"] is True


def test_planner_single_service(monkeypatch):
    import app.graph.nodes.planner as planner_mod

    # Patch the name as bound in the planner module (not the source module)
    monkeypatch.setattr(planner_mod, "chat", lambda msgs, **kw: _LICENCE_RESPONSE)

    state = {"goal": "renew my driving licence", "case_id": "c2", "user_id": "u1"}
    result = planner_mod.planner(state)

    assert result["detected_services"] == ["driving_license_renewal"]
    assert result["intent"]["has_blocking_issues"] is False


def test_planner_bad_json_degrades_gracefully(monkeypatch):
    import app.graph.nodes.planner as planner_mod

    monkeypatch.setattr(planner_mod, "chat", lambda msgs, **kw: "not json {{{{")

    state = {"goal": "something", "case_id": "c3", "user_id": "u1"}
    result = planner_mod.planner(state)

    assert result["detected_services"] == []
    assert isinstance(result["intent"], dict)


def test_planner_appends_audit_log(monkeypatch):
    import app.llm.groq_client as gc

    monkeypatch.setattr(gc, "chat", lambda msgs, **kw: _PLANNER_RESPONSE)

    from app.graph.nodes.planner import planner

    state = {"goal": "passport", "case_id": "c4", "user_id": "u1", "logs": []}
    result = planner(state)

    assert len(result.get("logs", [])) > 0
    assert result["logs"][0]["agent"] == "planner"


# ── Audit helper ──────────────────────────────────────────────────────────────


def test_audit_accumulates_log_entries():
    from app.graph.nodes.audit import audit

    state: dict = {"logs": []}
    update1 = audit(state, agent="planner", decision="detected X")
    assert len(update1["logs"]) == 1

    state2 = {**state, **update1}
    update2 = audit(state2, agent="knowledge", decision="found Y")
    assert len(update2["logs"]) == 2
    assert update2["logs"][1]["agent"] == "knowledge"


# ── Groq client ───────────────────────────────────────────────────────────────


def test_groq_chat_passes_json_mode(monkeypatch):
    """Verify json_mode sets response_format on the Groq call."""
    captured: dict = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return MagicMock(choices=[MagicMock(message=MagicMock(content='{"ok": true}'))])

    class FakeClient:
        chat = MagicMock(completions=FakeCompletions())

    import app.llm.groq_client as gc

    monkeypatch.setattr(gc, "_client", lambda: FakeClient())

    result = gc.chat([{"role": "user", "content": "hi"}], json_mode=True)
    assert captured.get("response_format") == {"type": "json_object"}
    assert result == '{"ok": true}'


# ── Runner (no Postgres) ──────────────────────────────────────────────────────


def test_runner_streams_events_without_db(monkeypatch):
    """Runner must yield SSE events even when checkpointer init fails."""
    import app.llm.groq_client as gc

    monkeypatch.setattr(gc, "chat", lambda msgs, **kw: _PLANNER_RESPONSE)

    # Force checkpointer to fail so we exercise the no-DB path
    import app.graph.runner as runner_mod

    monkeypatch.setattr(runner_mod, "_checkpointer", None)
    monkeypatch.setattr(runner_mod, "_cp_tried", False)
    monkeypatch.setattr(runner_mod, "_graph", None)

    async def _fake_ensure():
        return None

    monkeypatch.setattr(runner_mod, "_ensure_checkpointer", _fake_ensure)

    async def collect():
        chunks: list[str] = []
        async for chunk in runner_mod.run_case("case-x", "user-1", "I need a passport"):
            chunks.append(chunk)
        return chunks

    events = asyncio.run(collect())
    # At minimum the planner event should appear (other nodes are stubs returning {})
    assert any("planner" in e for e in events)
    assert any('"status"' in e for e in events)
