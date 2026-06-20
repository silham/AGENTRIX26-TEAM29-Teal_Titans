# M1 — Platform, Database & Auth

**Branch:** `feat/be-m1-platform`
**You are the foundation.** Everyone imports your models and depends on your auth
dependency. Land the scaffold + contracts first so the other four can start.

## Files you own

```
app/main.py                  app bootstrap, CORS, register ALL routers
app/config.py                pydantic-settings (env vars)
app/auth/jwt.py              verify NextAuth HS256 JWT → current_user
app/db/session.py            engine, SessionLocal, get_db dependency
app/db/models.py             SQLAlchemy models  ← SHARED CONTRACT
app/db/migrations/           alembic
app/repositories/cases.py    case persistence
app/repositories/steps.py    step persistence
app/schemas/case.py          pydantic DTOs for cases/steps
app/api/cases.py             case CRUD + list + "continue"
requirements.txt             seed the FULL shared dependency list
.env.example
tests/test_m1_*.py
```

## Responsibilities

1. **Scaffold commit (do this first, pair with M2).** Create every directory,
   `__init__.py`, seed `requirements.txt`, register every router in `main.py`
   (even the empty ones), and write `.env.example`. This unblocks the team.
2. **Data model (`db/models.py`) — the contract.** Implement exactly the schema in
   [IMPLEMENTATION_PLAN.md §7](../../../IMPLEMENTATION_PLAN.md):
   `cases, steps, documents, agent_logs, messages, doc_chunks`. Freeze column
   names early — other members code against them. Changes route through you.
3. **Auth (`auth/jwt.py`).** Verify the short-lived JWT minted by Next.js
   (HS256, shared `AUTH_SECRET`), extract `sub = user_id`, expose
   `get_current_user()` FastAPI dependency. Every protected route scopes by `user_id`.
4. **Case API (`api/cases.py`).** `POST /cases`, `GET /cases` (user's list),
   `GET /cases/{id}`, `DELETE /cases/{id}`. The "continue later" path returns the
   stored case + steps so the frontend can resume.
5. **Repositories.** CRUD helpers for cases/steps used by M2's runner and your API.

## Contracts you provide

- `db/models.py` column names (everyone reads these).
- `get_current_user` dependency (M2/M5 protect their routes with it).
- `get_db` session dependency.

## Definition of done

- `alembic upgrade head` builds all tables on a fresh Postgres + pgvector.
- A valid NextAuth JWT authenticates; an invalid one 401s.
- Can create, list, fetch, and delete a case via the API, scoped to the user.
