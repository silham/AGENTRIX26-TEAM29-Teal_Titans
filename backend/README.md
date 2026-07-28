# backend/ — HelpLK AI API

FastAPI + LangGraph + Postgres (pgvector). All AI on free tiers
(Groq, Gemini). See [../IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) for the
full architecture and [../PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) for the
file tree and ownership matrix.

## Run locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill GROQ_API_KEY, GEMINI_API_KEY, DATABASE_URL, AUTH_SECRET, ADMIN_EMAILS

# System binaries for OCR of scanned uploads (optional; uploads of scans fail
# with an actionable message without them):
#   macOS  : brew install tesseract poppler
#   Ubuntu : apt-get install tesseract-ocr poppler-utils

python -m app.db.init_db   # extension + tables (Postgres with pgvector)
alembic upgrade head       # column additions create_all() cannot make

uvicorn app.main:app --reload --port 8000   # docs at http://localhost:8000/docs
```

`DATABASE_URL` may be written as either `postgresql://` or `postgresql+psycopg://`
— `app/config.py` normalises it to psycopg3, which is the driver in
`requirements.txt`. Verify with:

```bash
python -c "from app.db.session import engine; print(engine.dialect.driver)"  # -> psycopg
```

Smoke test (no DB, API keys or Tesseract needed): `pytest`

### Migrations

Tables are still auto-created by `Base.metadata.create_all()` on import, but that
only ever creates **missing tables** — it never ALTERs an existing one. Column
additions therefore go through Alembic, and every revision is written with
idempotent SQL (`IF NOT EXISTS`) so the two mechanisms can coexist in any order.

- Existing database: `alembic upgrade head` (safe to re-run)
- Fresh database: `python -m app.db.init_db && alembic upgrade head`

If `doc_chunks` ever gets into a bad state, it holds only re-derivable data:
`DROP TABLE doc_chunks CASCADE`, then `python -m app.db.init_db && alembic upgrade head && python -m app.rag.ingest`.

## RAG knowledge layer (M3)

Hybrid RAG: deterministic JSON **rules** for dependency/eligibility/locking, plus
an **embedding** layer over government documents for citations and grounding.

```bash
# Populate doc_chunks from data/corpus/ (chunk -> embed -> store). Idempotent.
# Uses Gemini (gemini-embedding-001 @ 768 dims) when GEMINI_API_KEY is set, else
# a local sentence-transformers fallback so it works with zero quota.
python -m app.rag.ingest
```

> **Embedding models are not interchangeable.** The local fallback is 384-dim
> zero-padded to 768 — the same size as Gemini's vectors but a different vector
> space, so mixing them ranks by noise. Every chunk records the model that
> produced it (`doc_chunks.embedding_model`) and search filters on it. If you add
> or change `GEMINI_API_KEY`, **reindex** (`python -m app.rag.ingest`, plus
> Reindex for uploaded documents) so the whole corpus shares one model —
> otherwise retrieval correctly returns nothing. `GET /admin/knowledge/stats`
> shows the per-model breakdown.

Their score scales differ too, so the relevance floor is per-model
(`llm/embeddings.DEFAULT_MIN_SCORE`) rather than one global number:

| Model | Genuine matches | Unrelated documents | Floor |
| --- | --- | --- | --- |
| `gemini-embedding-001@768` | 0.60–0.77 | 0.43–0.46 | 0.55 |
| `all-MiniLM-L6-v2@384pad768` | 0.38–0.45 | — | 0.30 |

Set `RAG_MIN_SCORE` in `.env` to override both. Tune it against your own corpus
with `GET /admin/search?q=...&min_score=0`, which shows every raw score.

- Rules live in [`data/procedures/*.json`](data/procedures/) — one file per service
  (`requirements`, `depends_on`, `dependency_conditions`, `eligibility_rules`,
  `steps`, `source_url`). Loaded/queried by `app/rag/rules.py`.
- Corpus lives in [`data/corpus/*.txt`](data/corpus/) — each file starts with
  `source_url:` / `title:` header lines, then body text.
- Retrieval (`app/rag/retriever.py`) returns top-k chunks with their source URLs
  for clickable citations. The Knowledge node writes `requirements` + `citations`;
  the Dependency node builds the graph and locks blocked steps (e.g. a lost NIC
  locks the passport step behind the duplicate-NIC procedure).

## Admin knowledge base (M6)

Admins upload real government documents (PDF circulars, DOCX forms, scans) into
the same `doc_chunks` index the agent graph retrieves from. For goals no
procedure JSON covers, the Planner is given the retrieved passages and must cite
only URLs that appear in them — any URL it invents is stripped in Python, not
merely discouraged in the prompt.

**Who is an admin:** whoever is listed in `ADMIN_EMAILS` (comma-separated). That
email gets `role: "admin"` in its JWT, and `require_admin` re-checks the
allowlist on every request — so removing an email revokes access immediately
rather than after the token's 8-hour life.

```bash
# ADMIN_EMAILS=you@example.com in .env, then:
TOKEN=$(curl -s localhost:8000/auth/token -H 'content-type: application/json' \
  -d '{"email":"you@example.com"}' | python -c 'import sys,json;print(json.load(sys.stdin)["token"])')
AUTH="Authorization: Bearer $TOKEN"

curl -s -X POST localhost:8000/admin/knowledge -H "$AUTH" \
  -F 'file=@pension_circular_2024.pdf' \
  -F 'title=Public Service Pension Circular 2024' \
  -F 'source_url=https://pensions.gov.lk/circular-2024'   # 202, status "pending"

curl -s localhost:8000/admin/knowledge -H "$AUTH"          # poll until "ready"
curl -s localhost:8000/admin/knowledge/stats -H "$AUTH"    # counts + retrieval health
curl -s --get localhost:8000/admin/search -H "$AUTH" \
  --data-urlencode 'q=widow and orphans pension'           # retrieval smoke test
```

Accepted: PDF, DOCX, TXT, MD, and images (PNG/JPG/WEBP/TIFF/BMP). Scanned PDFs
and photos go through Tesseract; without poppler installed, page rendering is
skipped and embedded page images are OCR'd instead (lower fidelity, no system
dependency). When no OCR backend can read a file, the document is marked
`failed` with an actionable message shown verbatim in the admin UI.

Uploads are capped at `MAX_KNOWLEDGE_UPLOAD_MB` (default 20) and indexed in a
**background task**, hence the 202 — a 20-page scan is 20–60s of OCR, far past
the frontend's 15s request timeout. Background tasks die with the process, so a
restart marks anything stuck in `processing` as `failed` for the admin to retry.

`GET /admin/knowledge/stats` is also the place where retrieval failures become
visible: `retriever.search` deliberately returns `[]` rather than raising, so the
agent graph degrades instead of breaking, and this endpoint reports what actually
went wrong (wrong dialect, mixed embedding models, orphaned chunks).

UI: `/admin` in the frontend (upload, status, reindex, delete, retrieval test).
The nav entry and page guard are cosmetic — the enforced boundary is the `role`
claim plus `require_admin` on the server.

## Local auth testing (no frontend needed)

Protected routes expect the same HS256 JWT NextAuth will issue. Mint one locally
with the dev helper (signed with `AUTH_SECRET` from your `.env`):

```bash
python -m app.auth.mint_token                 # default user "dev-user-001", 24h
python -m app.auth.mint_token alice --hours 8 # custom user / expiry
```

Use it as a bearer token:

```bash
TOKEN=$(python -m app.auth.mint_token | head -1)
AUTH="Authorization: Bearer $TOKEN"

# Create a case
curl -s -X POST localhost:8000/cases -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"goal":"I lost my NIC and need to apply for a passport"}'

# List your cases · get one · stream the agent graph (SSE) · delete
curl -s localhost:8000/cases -H "$AUTH"
curl -s localhost:8000/cases/<id> -H "$AUTH"
curl -sN -X POST localhost:8000/cases/<id>/run -H "$AUTH"
curl -s -X DELETE localhost:8000/cases/<id> -H "$AUTH"
```

Tokens are verified by `app/auth/jwt.py`; every query is scoped by the token's
`sub` (user id), so one user never sees another's cases. The helper is **dev-only**
— in production the frontend mints the JWT.

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
