# backend/ — HelpLK AI API

FastAPI + LangGraph + LlamaIndex + Postgres (pgvector). All AI on free tiers
(Groq, Gemini). See [../IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) for the
full architecture and [../PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) for the
file tree and ownership matrix.

## Run locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill GROQ_API_KEY, GEMINI_API_KEY, DATABASE_URL, AUTH_SECRET

# Create tables (quick path). Needs a running Postgres with the pgvector extension available.
python -m app.db.init_db
# (Alternative: alembic revision --autogenerate -m "initial" && alembic upgrade head)

uvicorn app.main:app --reload --port 8000   # docs at http://localhost:8000/docs
```

Smoke test (no DB needed): `pytest`

## Team

Backend is divided across 5 members — one brief each in
[`docs/team/`](docs/team/):

- [M1 — Platform, DB & Auth](docs/team/MEMBER-1-platform-persistence.md)
- [M2 — Agent Orchestration (LangGraph)](docs/team/MEMBER-2-orchestration.md)
- [M3 — RAG & Knowledge](docs/team/MEMBER-3-rag-knowledge.md)
- [M4 — Eligibility, Checklist & Reminder](docs/team/MEMBER-4-workflow.md)
- [M5 — Documents & Forms](docs/team/MEMBER-5-documents.md)

## Conflict-free workflow

Each member owns a disjoint set of files (see the ownership matrix). A single
scaffold commit on `main` freezes the shared contracts (`db/models.py`,
`graph/state.py`, `schemas/run.py`) and stubs out every node and router, so
feature branches never touch the same file.
