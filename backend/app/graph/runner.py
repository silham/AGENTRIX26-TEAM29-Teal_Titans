"""Owner: M2. Stream graph execution as SSE RunEvents.

Checkpointer lifecycle
─────────────────────
A module-level async initialiser creates the AsyncPostgresSaver once and reuses
it for every request (connection pool lives for the process lifetime).  If the
DB is unavailable (e.g. dev without Postgres) the graph runs without a
checkpointer — no resume, but everything else works.

Resume flow
───────────
Pass `resume=True` when the user returns after an interrupt (upload/answer).
The graph reads the LangGraph checkpoint for `thread_id=case_id` and continues
from the interrupted node; no initial state is re-supplied.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from app.graph.builder import build_graph
from app.graph.state import GraphState
from app.schemas.run import RunEvent

# ── Checkpointer singleton ────────────────────────────────────────────────────

_checkpointer = None
_pool = None               # module-level ref keeps the pool alive for the process
_cp_lock = asyncio.Lock()
_cp_tried = False          # avoid retrying a failed init on every request


async def _ensure_checkpointer():
    """Initialise the AsyncPostgresSaver once (backed by a connection pool).

    A pool (not `from_conn_string`) for two reasons: the discarded context
    manager from `from_conn_string` gets GC-finalised at an arbitrary moment,
    closing its single connection mid-run ("the connection is closed"); and
    Neon's pooler drops idle connections, which a pool with a checkout
    health-check recovers from transparently.
    """
    global _checkpointer, _pool, _cp_tried
    if _checkpointer is not None or _cp_tried:
        return _checkpointer
    async with _cp_lock:
        if _checkpointer is not None or _cp_tried:
            return _checkpointer
        _cp_tried = True
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            from psycopg.rows import dict_row
            from psycopg_pool import AsyncConnectionPool
            from app.config import settings

            # psycopg3 needs a plain postgresql:// URL (not SQLAlchemy-prefixed)
            db_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
            pool = AsyncConnectionPool(
                db_url,
                min_size=1,
                max_size=4,
                open=False,
                check=AsyncConnectionPool.check_connection,  # revive dead conns on checkout
                kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
            )
            # Bounded waits so a hanging SSL handshake (e.g. channel_binding
            # mismatch) doesn't block the entire first /run request.
            await asyncio.wait_for(pool.open(wait=True, timeout=5.0), timeout=7.0)
            checkpointer = AsyncPostgresSaver(pool)
            await asyncio.wait_for(checkpointer.setup(), timeout=10.0)
            _pool = pool
            _checkpointer = checkpointer
        except Exception as exc:
            print(f"[runner] checkpointer init failed ({exc!r}); running without persistence")
            _checkpointer = None
    return _checkpointer


# ── Graph singleton (one compiled graph per checkpointer state) ───────────────

_graph = None


async def _get_graph():
    global _graph
    if _graph is not None:
        return _graph
    checkpointer = await _ensure_checkpointer()
    _graph = build_graph(checkpointer)
    return _graph


# ── SSE streaming ─────────────────────────────────────────────────────────────

_NODE_NAMES = frozenset(
    ["planner", "knowledge", "dependency", "run_eligibility", "run_checklist", "document", "form", "reminder"]
)


async def run_case(
    case_id: str,
    user_id: str,
    goal: str,
    language: str = "en",
    resume: bool = False,
    answers: dict | None = None,
) -> AsyncGenerator[str, None]:
    graph = await _get_graph()
    config = {"configurable": {"thread_id": case_id}}

    initial_state: GraphState | None = None
    if not resume:
        initial_state = {
            "case_id": case_id,
            "user_id": user_id,
            "goal": goal,
            "language": language,
            "facts": {},
            "interactive": _checkpointer is not None,
            "logs": [],
            "messages": [],
        }

    try:
        # Inject eligibility answers into state before resuming. Written "as"
        # the ask_user node so the graph continues into run_eligibility, which
        # re-evaluates with the new facts.
        if resume and answers and _checkpointer is not None:
            snap = await graph.aget_state(config)
            if snap and "ask_user" in tuple(snap.next or ()):
                existing = (snap.values or {}).get("facts") or {}
                await graph.aupdate_state(
                    config, {"facts": {**existing, **answers}}, as_node="ask_user"
                )

        async for chunk in graph.astream(
            initial_state,
            config=config,
            stream_mode="updates",
        ):
            for node_name, node_output in chunk.items():
                if node_name not in _NODE_NAMES:
                    continue
                yield RunEvent(agent=node_name, status="started").to_sse()
                yield RunEvent(
                    agent=node_name,
                    status="completed",
                    payload=node_output if isinstance(node_output, dict) else {},
                ).to_sse()

        # Distinguish "paused for eligibility answers" from "done": the stream
        # also ends when the graph hits an interrupt.
        if _checkpointer is not None:
            try:
                snap = await graph.aget_state(config)
                if snap and "ask_user" in tuple(snap.next or ()):
                    vals = snap.values or {}
                    yield RunEvent(
                        agent="system",
                        status="paused",
                        message="awaiting_answers",
                        payload={
                            "questions": vals.get("questions") or [],
                            "question_fields": vals.get("question_fields") or [],
                        },
                    ).to_sse()
                    return
            except Exception:
                pass

        yield RunEvent(agent="system", status="completed", message="done").to_sse()

    except Exception as exc:
        yield RunEvent(agent="system", status="error", message=str(exc)).to_sse()
