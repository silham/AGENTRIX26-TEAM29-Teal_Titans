# HelpLK AI — Project Structure & Backend Work Division

Top level has exactly two app folders:

```
agentrix/
├─ frontend/                 # Next.js app (separate track, not divided here)
├─ backend/                  # FastAPI + LangGraph + LlamaIndex (divided across 5 members)
├─ agents.md                 # product spec
├─ IMPLEMENTATION_PLAN.md    # build spec
└─ PROJECT_STRUCTURE.md      # this file
```

Per-member task briefs live in [`backend/docs/team/`](backend/docs/team/).

---

## Backend file tree (every file has ONE owner)

```
backend/
├─ app/
│  ├─ main.py                     M1   app bootstrap + registers ALL routers
│  ├─ config.py                   M1   env/settings
│  ├─ api/
│  │  ├─ cases.py                 M1   case CRUD, list, "continue"
│  │  ├─ run.py                   M2   POST /cases/{id}/run  (SSE stream)
│  │  ├─ documents.py             M5   upload / verify / delete document
│  │  └─ forms.py                 M5   form-assist endpoints
│  ├─ auth/
│  │  └─ jwt.py                   M1   verify NextAuth JWT → current_user dep
│  ├─ db/
│  │  ├─ session.py               M1   engine, SessionLocal, get_db
│  │  ├─ models.py                M1   SQLAlchemy models  ← shared CONTRACT
│  │  └─ migrations/              M1   alembic
│  ├─ repositories/
│  │  ├─ cases.py                 M1
│  │  ├─ steps.py                 M1
│  │  ├─ documents.py             M5
│  │  └─ logs.py                  M2   agent_logs writer (audit)
│  ├─ schemas/
│  │  ├─ case.py                  M1
│  │  ├─ document.py              M5
│  │  └─ run.py                   M2   SSE event shape ← shared CONTRACT
│  ├─ graph/
│  │  ├─ state.py                 M2   GraphState TypedDict ← shared CONTRACT
│  │  ├─ builder.py               M2   assemble nodes/edges + checkpointer
│  │  ├─ runner.py                M2   stream execution → SSE events
│  │  └─ nodes/
│  │     ├─ planner.py            M2
│  │     ├─ audit.py              M2   cross-cutting log helper
│  │     ├─ knowledge.py          M3   RAG retrieval node
│  │     ├─ dependency.py         M3   builds graph from JSON rules
│  │     ├─ eligibility.py        M4
│  │     ├─ checklist.py          M4
│  │     ├─ reminder.py           M4
│  │     ├─ document.py           M5
│  │     └─ form.py               M5
│  ├─ rag/
│  │  ├─ index.py                 M3   LlamaIndex + pgvector
│  │  ├─ ingest.py                M3   corpus ingestion CLI
│  │  ├─ retriever.py             M3
│  │  └─ rules.py                 M3   load procedures/*.json
│  ├─ llm/
│  │  ├─ groq_client.py           M2
│  │  ├─ gemini_vision.py         M5
│  │  └─ embeddings.py            M3
│  └─ documents/
│     ├─ storage.py               M5   bucket upload + signed URL
│     └─ ocr.py                   M5   tesseract fallback
├─ data/
│  ├─ procedures/*.json           M3   rules layer (dependencies/eligibility)
│  └─ corpus/                     M3   gov PDFs/HTML for embeddings
├─ tests/
│  ├─ test_m1_*.py                M1   (one test file prefix per member)
│  ├─ test_m2_*.py                M2
│  ├─ test_m3_*.py                M3
│  ├─ test_m4_*.py                M4
│  └─ test_m5_*.py                M5
├─ requirements.txt               M1   seeded full up front (see rules)
└─ .env.example                   M1
```

---

## Ownership matrix

| Member | Domain | Owns (directories / files) | Branch |
| --- | --- | --- | --- |
| **M1** | Platform, DB, Auth | `main.py`, `config.py`, `auth/`, `db/`, `repositories/{cases,steps}.py`, `schemas/case.py`, `api/cases.py`, `requirements.txt`, `.env.example` | `feat/be-m1-platform` |
| **M2** | Agent orchestration | `graph/{state,builder,runner}.py`, `graph/nodes/{planner,audit}.py`, `repositories/logs.py`, `schemas/run.py`, `api/run.py`, `llm/groq_client.py` | `feat/be-m2-orchestration` |
| **M3** | RAG & Knowledge | `rag/`, `data/`, `graph/nodes/{knowledge,dependency}.py`, `llm/embeddings.py` | `feat/be-m3-rag` |
| **M4** | Eligibility, Checklist, Reminder | `graph/nodes/{eligibility,checklist,reminder}.py` | `feat/be-m4-workflow` |
| **M5** | Documents & Forms | `documents/`, `api/{documents,forms}.py`, `graph/nodes/{document,form}.py`, `repositories/documents.py`, `schemas/document.py`, `llm/gemini_vision.py` | `feat/be-m5-documents` |

No file appears in two rows → branches never edit the same file → merges are conflict-free.

---

## The three shared CONTRACTS (frozen in the scaffold commit)

Conflicts only happen on shared files. We eliminate them by freezing three
contracts in a **single scaffold commit on `main`** before parallel work starts,
authored together by M1 + M2:

1. **`db/models.py` (M1)** — table columns every member reads/writes.
2. **`graph/state.py` (M2)** — the `GraphState` dict passed between nodes.
3. **`schemas/run.py` (M2)** — the SSE event JSON the frontend consumes.

Plus the **node interface**: every node is
`def <name>(state: GraphState) -> dict` returning a partial state update, living
in its own file under `graph/nodes/`. The scaffold commit creates **stub** nodes
(return `{}`) and `builder.py` already importing all of them, so M2 never edits a
file when a member finishes their node — the import already exists.

After the scaffold commit, changing a contract requires a 2-minute sync with its
owner (M1 or M2); members never edit contracts in parallel.

---

## Rules that keep git conflict-free

1. **Edit only files in your ownership row.** Need a change elsewhere? Ping the owner.
2. **One scaffold commit first.** All directories, `__init__.py`, stub nodes,
   router registrations, and the 3 contracts land on `main` before anyone branches.
3. **`requirements.txt` is seeded complete by M1** in the scaffold (fastapi,
   uvicorn, sqlalchemy, alembic, psycopg, pydantic, python-jose, langgraph,
   langgraph-checkpoint-postgres, llama-index, llama-index-vector-stores-postgres,
   groq, google-generativeai, pgvector, pillow, pytesseract). Members should rarely
   touch it; if you must, append at the end on your own line.
4. **`main.py` pre-registers every router** in the scaffold, so members fill in
   their own `api/*.py` without touching `main.py`.
5. **`builder.py` pre-imports every node stub** in the scaffold, so members fill in
   their own `graph/nodes/*.py` without touching `builder.py`.
6. **Tests are namespaced by member** (`test_m{N}_*.py`) — no shared test file.
7. **Rebase on `main` before opening a PR**; since files don't overlap, this is clean.
