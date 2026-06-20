# HelpLK AI — Implementation Plan

> Companion to [agents.md](agents.md). This file is the **build spec**: locked
> tech decisions, architecture, data model, and an ordered task list.
> All third-party AI services used here are on **free tiers** (Groq, Gemini, Supabase, Vercel, NextAuth).

---

## 1. Locked Decisions

| Area | Decision | Why |
| --- | --- | --- |
| Backend | **FastAPI (Python)** | Best home for LangGraph + LlamaIndex; authentic "agent graph" story for judges. |
| Agent orchestration | **LangGraph** | Real stateful graph with checkpoints + human-in-the-loop interrupts → directly answers the "long session" requirement. |
| RAG | **LlamaIndex, hybrid** | JSON rules for dependency/eligibility (deterministic) + embeddings over a real gov corpus (citations). |
| Frontend | **Next.js (App Router) + Tailwind + shadcn/ui + Framer Motion** | One polished SPA-feel UI; Framer powers the agent-processing animation. |
| Auth | **NextAuth (Auth.js)** in the Next.js layer | Email magic-link (Resend free) or Google OAuth; sessions in Postgres. |
| DB / vectors | **Postgres + pgvector** (Supabase or Neon free tier) | Single data plane for NextAuth, domain state, LangGraph checkpoints, and embeddings. |
| File storage | **Supabase Storage private bucket** (or Cloudflare R2) | Encrypted-at-rest, served only via authorized backend. |
| Reasoning LLM | **Groq** (Llama 3.3 70B) | Free, very fast; planner, dependency, eligibility, form, what-if. JSON mode for structured output. |
| Vision / OCR / translate / embeddings | **Gemini 1.5 Flash** (free tier) + `text-embedding-004` | Document verification, Sinhala/Tamil/English, embeddings. |
| OCR fallback | **Tesseract** (`pytesseract`) | Works with zero quota. |

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Next.js (App Router) — Vercel                            │
│  • UI: Tailwind + shadcn/ui + Framer Motion               │
│  • NextAuth (magic link / Google) → sessions in Postgres  │
│  • Route handlers proxy to FastAPI, attach signed JWT     │
│  • SSE consumer → live "agent processing" animation       │
└───────────────┬──────────────────────────────────────────┘
                │ HTTPS + Bearer JWT (HS256, shared AUTH_SECRET)
┌───────────────▼──────────────────────────────────────────┐
│  FastAPI (Python) — Render / Railway / Fly (free)         │
│  • Verifies NextAuth JWT → user_id (app-level authz)      │
│  • LangGraph orchestrator (the agent graph)               │
│  • LangGraph Postgres checkpointer (resumable state)      │
│  • LlamaIndex hybrid RAG (JSON rules + pgvector)          │
│  • LLM clients: Groq (reasoning), Gemini (vision/embed)   │
│  • Streams node-by-node progress over SSE                 │
└───────────────┬──────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────┐
│  Postgres + pgvector  (Supabase / Neon free)              │
│  • NextAuth: users, accounts, sessions, verification      │
│  • Domain: cases, steps, documents, agent_logs, messages  │
│  • LangGraph: checkpoints (thread_id = case_id)           │
│  • Vectors: doc_chunks (embedding + source_url)           │
│  Supabase Storage (private) — uploaded documents          │
└──────────────────────────────────────────────────────────┘
```

---

## 3. State Retention (the "long session" answer)

Two complementary layers, both in Postgres:

1. **Durable domain state — source of truth.**
   `cases / steps / documents / agent_logs` hold the citizen's real progress.
   The dashboard reads these; "Continue my passport process" resumes from here.
   Survives indefinitely, fully queryable and auditable.

2. **Agent working memory — LangGraph checkpointer.**
   The graph is checkpointed to Postgres with `thread_id = case_id`. A run can
   **pause mid-graph** (waiting on a document upload or a clarifying answer) via
   LangGraph `interrupt()`, then **resume** later without re-running prior nodes.
   This is what makes sessions long-lived and stateful rather than one-shot.

**Resume flow:** user returns → front-end loads case from domain tables →
on "continue", backend resumes the LangGraph thread from its last checkpoint.
Conversation history persists in `messages` (and inside the checkpoint).

---

## 4. Auth Flow (NextAuth + separate Python backend)

1. User logs in via NextAuth (magic link through Resend free tier, or Google OAuth).
   Sessions persist in Postgres via the NextAuth adapter (Drizzle/Prisma).
2. When Next.js calls FastAPI, it mints a **short-lived JWT** signed with the
   shared `AUTH_SECRET` (HS256), payload `{ sub: user_id, exp }`.
3. FastAPI verifies that JWT with the same secret and scopes **every** query by
   `user_id`. No second login system — Next.js owns identity, FastAPI trusts the token.
4. Optional hardening: Postgres RLS keyed by `user_id` if on Supabase.

---

## 5. Hybrid RAG Design

- **Rules layer** — `backend/data/procedures/*.json`. One file per service:
  ```json
  {
    "id": "passport_application",
    "name": "Passport Application",
    "office": "Department of Immigration & Emigration",
    "requirements": ["valid_nic", "birth_certificate", "passport_photos", "application_form"],
    "depends_on": ["valid_nic"],
    "eligibility_rules": [{"field": "citizenship", "equals": "sri_lankan"}],
    "steps": [ { "title": "...", "description": "...", "source_url": "..." } ],
    "source_url": "https://www.immigration.gov.lk/..."
  }
  ```
  Drives the **dependency graph, step locking, and checklist deterministically** —
  never left to the LLM, so behavior is reliable in the demo.

- **Embedding layer** — ~15–20 real SL gov pages/PDFs (passport, NIC/DRP,
  driving licence/RMV, birth certificate/Registrar) chunked and embedded into
  `pgvector` via LlamaIndex. Powers free-text "why / explain" answers and
  **clickable citations**.

- **Trust rule:** dependency/eligibility/locking = JSON; narrative + citations = embeddings.
  Always separate "verified fact (with source)" from "AI suggestion" in the UI.

---

## 6. Agent Graph (LangGraph)

Nodes, with conditional edges and interrupts:

```
START
  → Planner            (Groq: goal → detected services, intent)
  → RAG Knowledge      (LlamaIndex: requirements + citations)
  → Dependency         (JSON: build graph, lock blocked steps)
  → Eligibility        (JSON rules + Groq: minimal questions, blockers)
  → Checklist          (compose ordered tasks + progress %)
  → [interrupt] await user / document upload
  → Document Verify    (Gemini Vision / Tesseract on upload)
  → Form Assistant     (Groq: explain/validate fields, on demand)
  → Reminder           (compute due/expiry/idle nudges)
  → END
Audit/Trust  = cross-cutting; every node writes an agent_logs row
               (decision, reason, source, confidence).
```

Node updates **stream over SSE** to the front-end — the processing animation
reflects real agent execution, not a fake timer.

---

## 7. Data Model (Postgres)

```sql
-- NextAuth tables: users, accounts, sessions, verification_tokens (via adapter)

cases       (id, user_id, goal, status, progress, current_step_id, language, created_at, updated_at)
steps       (id, case_id, ord, title, description, status, depends_on jsonb, source_url, reason)
            -- status: pending | active | completed | locked | skipped
documents   (id, case_id, name, type, storage_path, status, issues jsonb, uploaded_at)
            -- status: missing | accepted | rejected | incomplete | needs_verification
agent_logs  (id, case_id, agent, decision, reason, source_url, confidence, created_at)
messages    (id, case_id, role, content, created_at)
doc_chunks  (id, source_url, title, content, embedding vector(768))
-- langgraph checkpoints table created by langgraph-checkpoint-postgres
```

---

## 8. Repository Layout

```
agentrix/
├─ frontend/                 # Next.js
│  ├─ app/(routes)/          # landing, goal, processing, workflow, checklist, dashboard, case/[id]
│  ├─ app/api/               # NextAuth route + proxy handlers to FastAPI
│  ├─ components/            # shadcn/ui, AgentCard, StepList, Checklist, ExplainPanel
│  └─ lib/                   # api client, auth helpers, jwt minting
├─ backend/                  # FastAPI
│  ├─ app/main.py            # routes: /cases, /cases/{id}/run (SSE), /documents, /forms
│  ├─ app/auth.py            # verify NextAuth JWT
│  ├─ app/graph/             # LangGraph nodes + builder + checkpointer
│  ├─ app/rag/               # LlamaIndex index, ingestion, retrieval
│  ├─ app/llm/               # groq_client.py, gemini_client.py
│  ├─ app/db/                # SQLAlchemy models, migrations
│  └─ data/procedures/*.json # rules layer
│  └─ data/corpus/           # gov PDFs/HTML for embeddings
├─ IMPLEMENTATION_PLAN.md
└─ agents.md / CLAUDE.md
```

---

## 9. Build Order (time-boxed for a 12h MVP)

| Phase | Time | Output |
| --- | --- | --- |
| **0. Scaffold** | 0.5h | Repos, env vars, Postgres + pgvector up, health checks both services. |
| **1. Data layer** | 2h | `procedures/*.json` for the 3 demo flows (passport-after-NIC, licence renewal, birth cert); SQLAlchemy schema + migrations; ingest ~15 docs → `doc_chunks`. |
| **2. Agent graph** | 3h | LangGraph nodes wired to Groq + Gemini + hybrid RAG; Postgres checkpointer; `/cases/{id}/run` streams SSE; writes domain tables + agent_logs. |
| **3. Frontend** | 3h | All 8 screens; live agent-processing animation from SSE; workflow with locked steps; checklist; explainability panel with citations. |
| **4. Auth + persistence** | 1.5h | NextAuth (magic link), JWT to FastAPI, dashboard lists user's cases, "continue later" resumes checkpoint. |
| **5. Documents** | 1h | Upload to private bucket → Gemini Vision validation → checklist updates. |
| **6. Polish + demo** | 1h | Sinhala/Tamil/English selector, seed demo case, reminders, full dry run of the NIC→passport script. |

**Critical path / demo guarantee:** the *"I lost my NIC and need a passport"*
flow must work end-to-end before any secondary feature. Build it as a vertical
slice in Phases 1–3, then layer auth/docs/polish around it.

---

## 10. Data Safety (hackathon-appropriate, production-shaped)

- Private storage bucket; documents reachable only through an authorized backend
  endpoint that checks `user_id`. Encrypted at rest (Supabase/R2 default).
- All domain queries scoped by `user_id`; optional Postgres RLS.
- `DELETE /documents/{id}` and `DELETE /cases/{id}` — citizen can erase their data.
- PII minimization: store only what a step needs; never log raw document contents.
- `agent_logs` give an audit trail (decision + reason + source + confidence).
- UI always separates **verified fact (with source)** from **AI suggestion**.
- Secrets in env only; `AUTH_SECRET` shared between Next.js and FastAPI for JWT.

---

## 11. Free-Tier Service Checklist

- [ ] Groq API key (reasoning)
- [ ] Gemini API key (vision, embeddings, translation)
- [ ] Supabase project (Postgres + pgvector + Storage) **or** Neon + Cloudflare R2
- [ ] Resend API key (NextAuth magic link) — or Google OAuth client
- [ ] Vercel (frontend) + Render/Railway/Fly (backend)
- [ ] `AUTH_SECRET` generated and shared between the two services
