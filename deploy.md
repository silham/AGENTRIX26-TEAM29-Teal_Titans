# Deploying HelpLK AI on Coolify

This repo deploys as two containers — `frontend` (Next.js) and `backend`
(FastAPI) — defined in [docker-compose.yml](docker-compose.yml). Postgres is
**not** part of the stack; you bring an external Postgres + pgvector database
(Supabase or Neon free tier, per [agents.md](agents.md)).

## 1. Prerequisites

- A Coolify instance (v4+) with a server attached.
- An external Postgres database with the `vector` extension available —
  Supabase or Neon free tier both work. Grab its connection string.
- API keys: `GROQ_API_KEY` (Groq), `GEMINI_API_KEY` (Google AI Studio). Both
  are free-tier; the app degrades gracefully without them but planning/RAG
  quality suffers.
- This repo pushed to a Git provider Coolify can reach (GitHub/GitLab/etc.).

## 2. Create the resource

1. In Coolify: **+ New → Docker Compose**.
2. Point it at this repository and branch. Coolify will read
   `docker-compose.yml` from the repo root.
3. Do **not** deploy yet — set environment variables first (next section).

## 3. Environment variables

Set these in Coolify's **Environment Variables** tab for the resource (copy
from [.env.example](.env.example)). Coolify injects them for both build and
runtime, which matters because `NEXT_PUBLIC_BACKEND_URL` is a build arg.

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | yes | `postgresql+psycopg://user:pass@host:5432/db`. Must already support (or allow creating) the `vector` extension — the backend runs `CREATE EXTENSION IF NOT EXISTS vector` on every startup. |
| `AUTH_SECRET` | yes | Any long random string. **Must be identical** on frontend and backend — it's the shared HS256 JWT secret. Generate with `openssl rand -hex 32`. |
| `FRONTEND_ORIGIN` | yes | Public frontend URL (e.g. `https://helplk.example.com`). Used for backend CORS. Comma-separate for multiple origins. |
| `NEXT_PUBLIC_BACKEND_URL` | yes | Public backend URL (e.g. `https://api.helplk.example.com`). **Baked into the frontend's client JS at build time** — the browser calls this directly for streaming agent runs, so it cannot be the internal Docker service name. |
| `ADMIN_EMAILS` | no | Comma-separated emails granted `/admin/*` access (knowledge-base uploader). |
| `GROQ_API_KEY` | no | Powers planner/dependency/eligibility/form/what-if agents. |
| `GEMINI_API_KEY` | no | Powers document vision, translation, embeddings. Falls back to a local zero-quota embedding model if unset. |

## 4. First deploy and domain assignment

There's a chicken-and-egg step because `NEXT_PUBLIC_BACKEND_URL` must be a
real public URL, but you don't have Coolify-assigned domains until a service
exists:

1. Deploy once with placeholder values for `FRONTEND_ORIGIN` /
   `NEXT_PUBLIC_BACKEND_URL` (or your best guess at the final domains, if
   using custom domains you already control).
2. In Coolify, open the resource and assign a domain to the `frontend`
   service (port 3000). Assign a domain to the `backend` service (port 8000)
   too if you want `/docs` or `/admin` reachable directly.
3. Update `FRONTEND_ORIGIN` and `NEXT_PUBLIC_BACKEND_URL` to the real
   assigned domains.
4. Redeploy. This step **rebuilds the frontend image** (required, since the
   backend URL is compiled into the client bundle) — a restart alone will
   not pick up the change.

## 5. What happens on startup

`backend`'s entrypoint ([backend/docker-entrypoint.sh](backend/docker-entrypoint.sh))
runs automatically on every deploy, before `uvicorn` starts:

1. Polls `DATABASE_URL` until it accepts connections (up to ~60s).
2. `python -m app.db.init_db` — creates the `vector` extension and any
   missing tables (idempotent; never alters existing tables).
3. `alembic upgrade head` — applies column-level migrations (idempotent,
   safe to re-run).

No manual migration step is needed on redeploy.

## 6. Storage

Uploaded citizen documents are written to `/app/storage` inside the
`backend` container, persisted via the `backend_storage` named volume. This
is local disk, not object storage — if you later move the backend across
hosts, migrate that volume's contents too, or swap in Supabase Storage / R2
per the "future enhancements" note in [agents.md](agents.md).

## 7. Verifying the deploy

```bash
curl -f https://api.yourdomain.com/docs        # backend up, FastAPI docs render
curl -f https://yourdomain.com                  # frontend up
```

Then in the browser: submit a goal (e.g. "I lost my NIC and need a
passport") and confirm the agent-processing view streams events — this
exercises the frontend → backend SSE path end-to-end, which is exactly the
path `NEXT_PUBLIC_BACKEND_URL` must be correct for.

## Troubleshooting

- **CORS errors in the browser console**: `FRONTEND_ORIGIN` on the backend
  doesn't match the frontend's actual origin (scheme + host, no trailing
  slash).
- **401s / "invalid token" after login**: `AUTH_SECRET` differs between
  `frontend` and `backend`, or one side is still on the placeholder value
  from step 4.
- **Frontend calls fail with a CORS or connection error to `localhost:8000`**:
  `NEXT_PUBLIC_BACKEND_URL` wasn't set at build time — redeploy (a plain
  restart won't rebuild the bundle).
- **Backend crash-loops at startup**: check `DATABASE_URL` connectivity (the
  entrypoint's DB wait step logs each retry) and that the DB user can run
  `CREATE EXTENSION IF NOT EXISTS vector`.
