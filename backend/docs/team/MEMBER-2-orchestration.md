# M2 — Agent Orchestration (LangGraph)

**Branch:** `feat/be-m2-orchestration`
**You own the agent graph** — the core "agentic" story. You define the state
contract and wire everyone's nodes together. Pair with M1 on the scaffold commit.

## Files you own

```
app/graph/state.py           GraphState TypedDict  ← SHARED CONTRACT
app/graph/builder.py         assemble nodes + edges + Postgres checkpointer
app/graph/runner.py          stream execution → SSE events
app/graph/nodes/planner.py   Planner node (Groq)
app/graph/nodes/audit.py     cross-cutting audit/trust log helper
app/repositories/logs.py     agent_logs writer
app/schemas/run.py           SSE event shape  ← SHARED CONTRACT
app/api/run.py               POST /cases/{id}/run  (SSE)
app/llm/groq_client.py       Groq (Llama 3.3 70B) wrapper, JSON mode
tests/test_m2_*.py
```

## Responsibilities

1. **`graph/state.py` — the contract.** Define `GraphState` (e.g. `goal`,
   `user_id`, `case_id`, `language`, `detected_services`, `requirements`,
   `dependency_graph`, `eligibility`, `checklist`, `documents`, `messages`,
   `citations`, `logs`). Freeze the keys — every node reads/writes these.
2. **Node interface + stubs (in the scaffold commit).** Establish
   `def node(state: GraphState) -> dict`. Create stub files for **all** nodes
   (return `{}`) and have `builder.py` import every one, so M3/M4/M5 just fill in
   their stub without ever editing `builder.py`.
3. **`builder.py`.** Wire the graph (Planner → Knowledge → Dependency →
   Eligibility → Checklist → Document/Form on demand → Reminder), conditional
   edges, and an **`interrupt()`** point to pause for uploads/answers. Attach the
   **`PostgresSaver` checkpointer** with `thread_id = case_id` — this is the
   resumable-session mechanism.
4. **`runner.py` + `api/run.py`.** Stream graph execution; emit one SSE event per
   node (`{agent, status, payload}`) matching `schemas/run.py`. This drives the
   frontend "agent processing" animation. On resume, continue from the checkpoint.
5. **Planner node.** Goal text → detected services + intent (Groq JSON mode).
6. **Audit helper + `logs.py`.** Wrapper every node calls to write an `agent_logs`
   row (`agent, decision, reason, source_url, confidence`).
7. **`groq_client.py`.** Shared Groq wrapper (chat + JSON mode). M3/M4 import it.

## Contracts you provide

- `GraphState` keys, the node signature, and the SSE event shape.
- `groq_client` (M3 dependency, M4 eligibility/form reasoning).
- `audit.log(...)` helper (all nodes call it).

## Definition of done

- `POST /cases/{id}/run` streams node-by-node SSE events end to end.
- Killing the run mid-graph and re-calling resumes from the checkpoint (same `case_id`).
- Every node execution writes an `agent_logs` row.
