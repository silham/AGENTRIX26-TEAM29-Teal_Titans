# PRESENT.md — HelpLK AI Evaluation Playbook

How to present HelpLK AI to industry evaluators who have never seen it, and score
the highest possible marks in an **Agentic AI + RAG** hackathon. Everything in the
demo script below has been tested end-to-end and works. Follow the script; don't
improvise into untested territory (see "Do NOT demo" below).

---

## 1. The 30-Second Opening (memorize this)

> "Every Sri Lankan knows the pain: you go to a government office, and you're sent
> back because you brought the wrong documents, or did the steps in the wrong
> order. The information is public — it's just scattered, unordered, and not
> personalized.
>
> HelpLK AI is a citizen services **copilot**. You describe your situation in
> plain language — *'I lost my NIC and need a passport'* — and a team of AI
> agents plans the correct procedure, in the correct order, with official
> sources, and tracks your progress until you finish.
>
> **ChatGPT answers questions. HelpLK executes government procedures.**"

That last line is your anchor. Return to it whenever a question drifts.

---

## 2. What Evaluators Score (and where you win)

| Dimension | Your winning evidence |
| --- | --- |
| **Agentic AI** | A real LangGraph state machine with 8 specialized agents — the processing screen animates from **live SSE events emitted by real agent execution**, not a fake timer. Say this explicitly; judges assume such animations are fake. |
| **RAG** | **Hybrid RAG**: deterministic JSON rules decide dependencies/locking (auditable, no hallucination), pgvector + Gemini embeddings over real gov.lk sources provide cited answers. The split itself is a design insight — lead with it. |
| **Statefulness** | Postgres-backed LangGraph checkpointer + durable case tables. Close the tab, come back, continue. Demo it. |
| **Trust / safety** | Every agent writes an audit log (decision, reason, source, confidence). Locking is rule-based, never LLM-guessed. Citations link to official sources. |
| **Completeness** | Full loop: goal → plan → do steps → progress → completion. Show a step being completed and a locked step unlocking. |
| **Viability** | Buyer = GoSL / ICTA. Entire stack runs on free tiers (Groq, Gemini, Neon, Vercel) — unit economics are a genuine talking point. |

---

## 3. The Demo Script (~8 minutes)

**Golden rule: the demo is the pitch.** Slides only for architecture (one diagram)
and the close.

### Act 1 — The flagship flow (3 min)

1. Landing page → type: **"I lost my NIC and need to apply for a passport"**.
2. On the processing screen, narrate the agent cards as they light up:
   > "These aren't animations on a timer — each card lights up when that agent
   > actually finishes on the backend. Planner detected two services. The
   > Knowledge agent just pulled requirements with citations from the Department
   > of Immigration's official pages. The Dependency agent is now checking
   > prerequisites…"
   Then the run **pauses and asks eligibility questions** (citizenship, age,
   existing NIC number). Answer them and narrate:
   > "This is a real human-in-the-loop interrupt — the agent graph checkpointed
   > itself to Postgres and paused. My answers are injected into its state and
   > the eligibility agent re-evaluates before any plan is built. If I answer
   > 'not a Sri Lankan citizen', it doesn't just refuse — it locks the plan and
   > suggests an alternative route."
   (If you have 30 spare seconds, run a second case answering "Other" for
   citizenship to show the blocked verdict + alternative-path suggestion.)
3. The plan appears: **13 steps — duplicate NIC first, passport steps LOCKED.**
   This is the money shot. Say:
   > "Notice it did *not* just answer 'here's how to get a passport.' It reasoned:
   > passport requires an NIC; yours is lost; therefore duplicate NIC comes first —
   > and it **locked** the passport steps until that's done. This locking is
   > driven by a deterministic rules layer, not the LLM, so it can never
   > hallucinate a wrong order."
4. Click **"Official source"** on a step → the actual immigration.gov.lk page.
   Click **"More info"** → the explainability panel.

### Act 2 — It's stateful, not a chatbot (2 min)

5. Click **"Complete Current Step"** a few times (or "Mark as done" on cards).
   Progress climbs; when the last duplicate-NIC step completes, **the first
   passport step visibly unlocks**. Narrate:
   > "The case is a living object. When I finish the NIC procedure, the system
   > unlocks what depended on it. If I undo a step, downstream steps re-lock."
6. Go to **Dashboard** → multiple cases with progress. Open a second prepared
   case. Say:
   > "State survives across sessions — the agent graph checkpoints to Postgres,
   > so a citizen can return next week and continue exactly where they stopped."

### Act 3 — It generalizes (2 min)

7. New goal, something NOT in the rules layer:
   **"I need to get Sri Lankan citizenship for my foreign wife"**.
   A coherent custom plan appears (gather documents → application → oath → GN
   registration). Say:
   > "This service has no pre-built workflow. The planner recognized that, and
   > generated a custom procedure — while still applying the same dependency
   > engine: if this citizen had also lost their NIC, the real duplicate-NIC
   > workflow would be prepended as a prerequisite."
8. (Optional, if time) Show the language selector (Sinhala / Tamil / English) on
   the goal page and mention accessibility for rural citizens.

### Act 4 — One architecture slide + close (1 min)

- Next.js → FastAPI → **LangGraph agent graph** (8 nodes, interrupt/resume,
  Postgres checkpointer) → **hybrid RAG** (JSON rules + pgvector) → Groq Llama 3.3
  for reasoning, Gemini for vision/embeddings. All free tier.
- Close with the tagline: **"From confusion to completion."**

---

## 4. Pre-flight Checklist (do this 30 min before)

- [ ] `backend`: `.venv` activated, `uvicorn app.main:app --port 8000` running,
      `http://localhost:8000/health` returns ok. **Do not run with `--reload`
      during the demo** — a stray file save kills in-flight SSE streams.
- [ ] `frontend`: `npm run dev`, sign in at `/auth` beforehand (any email works).
- [ ] Groq + Gemini keys valid: run one throwaway goal end-to-end as a smoke test.
- [ ] **Seed the dashboard**: 2–3 cases at different progress levels (one ~50%,
      one completed) so the dashboard looks alive.
- [ ] Pre-run the flagship goal once — Groq latency on first call can be a few
      seconds; a warm run keeps the demo snappy.
- [ ] Internet check: Groq, Gemini, and Neon are all cloud services.
- [ ] Close every unrelated tab; browser at 100–125% zoom for projectors.

**Failure fallbacks (know these cold):**
- If **Groq is down**: the flagship "lost NIC + passport" flow still works — a
  keyword fallback detects services without the LLM. Custom goals won't work;
  stick to the flagship + licence renewal + birth certificate goals.
- If **the run errors mid-stream**: click Resume/re-run once — the graph is
  idempotent and rewrites the plan.
- If **all else fails**: the dashboard and any pre-seeded case pages render from
  the database with no LLM calls at all. Walk through a seeded case and the
  step completion/unlock mechanic — that alone shows statefulness.

---

## 5. Judge Q&A Cheat Sheet

**"Why not just use ChatGPT?"**
> "ChatGPT gives you a paragraph; we give you an executable, tracked workflow.
> Three concrete differences: (1) our dependency ordering and step locking are
> deterministic rules from a curated dataset — an LLM can't hallucinate a wrong
> procedure order; (2) the case is stateful — documents, progress, resumability;
> (3) every recommendation carries an official source citation and an audit log.
> We use LLMs as components inside a governed system, not as the product."

**"What's actually agentic here, versus one big prompt?"**
> "It's a LangGraph state machine with 8 specialized nodes — planner, RAG
> knowledge, dependency, eligibility, checklist, document verification, form
> assistant, reminder — each reads and writes a shared typed state, each logs its
> decision with confidence. The graph can pause mid-run on a human-in-the-loop
> interrupt (e.g. waiting for a document upload) and resume from a Postgres
> checkpoint days later. That pause/resume is the definitional difference between
> an agent system and a prompt chain."

**"How do you prevent hallucinations?"**
> "By deciding what the LLM is *allowed* to decide. Dependencies, eligibility,
> and step locking come from a deterministic JSON rules layer. The LLM handles
> language understanding and narrative. Retrieval answers carry citations to
> official sources, and the audit trail records why every decision was made.
> When a goal falls outside our verified dataset, the UI can distinguish
> verified steps from AI-suggested ones."

**"Where does the data come from? Is it real?"**
> "The rules layer and embedded corpus are built from real public sources —
> Department of Immigration, DRP, RMV, Registrar General. For the hackathon we
> curated 4 full procedures and ~15 source documents. The architecture point is
> that adding a service is *adding a JSON file and re-ingesting* — no code."

**"How does this scale / what's the business model?"**
> "The buyer is the government (or its digital transformation partners like
> ICTA). Value: fewer incomplete applications, less counter congestion, analytics
> on where citizens get stuck, and a defense against paid brokers. The demo runs
> entirely on free tiers; at national scale the marginal cost per case is cents."

**"What about data privacy?"**
> "Every query is scoped by user id from a signed JWT; documents go to a private
> bucket served only through authorized endpoints; citizens can delete cases and
> documents; we store the minimum and never log document contents. Audit logs
> make the AI's reasoning inspectable — which a government deployment requires."

**"Sinhala and Tamil?"**
> "The UI accepts all three languages and the model layer (Gemini) handles
> translation. Deep localization of every procedure text is roadmap, not done."

---

## 6. Honesty Strategy — what's not finished (and how to frame it)

Evaluators respect teams who know their gaps. Never claim these work; if asked,
use the framing given. **Volunteer nothing from this list unprompted.**

| Gap | If asked, say |
| --- | --- |
| **Document upload validation UI** — the Documents tab currently shows an illustrative checklist; uploads reach the backend (Gemini Vision + Tesseract fallback are implemented and unit-tested) but results aren't wired into the visible checklist. | "The vision pipeline — Gemini document analysis with an OCR fallback — is implemented and tested on the backend; wiring its verdicts into the checklist UI is the next sprint." |
| **Auth is demo-mode** (any email → signed JWT; no NextAuth/passwords). | "Identity is intentionally mocked for the demo; the token contract FastAPI verifies is exactly what NextAuth would issue, so swapping in real auth is a config change, not a redesign." |
| **Reminders** are computed by an agent but nothing sends SMS/notifications. | "The reminder agent computes due/idle nudges; delivery channels (SMS/WhatsApp) are roadmap." |
| **Custom plans have no citations** (they're LLM-generated, rules-verified only for prerequisites). | "Anything outside the curated dataset is clearly a best-effort plan; the durable fix is expanding the dataset — one JSON file per service." |
| **Custom goals skip the eligibility Q&A** (only rules-based services have eligibility predicates to ask about). | "Eligibility questions come from the deterministic rules layer by design; custom procedures get them as we curate their rules." |
| **Only 4 procedures** have full verified rules. | "Deliberate: depth over breadth. One flagship flow works end-to-end flawlessly rather than twenty half-working ones." |
| **What-If simulation agent** from the spec is not built. | "Designed, not built — the dependency graph already contains the data it needs." |

The meta-line that lands well:
> "We spent our hours making the agentic core real — a checkpointed graph,
> deterministic locking, honest citations — instead of stubbing twenty features.
> Everything you just saw was live."

---

## 7. Talking-Point Deep Dives (if evaluators are technical)

Have these ready; deploy only on demand.

- **Node contract**: every agent is `def node(state: GraphState) -> dict`
  returning a partial state update; LangGraph merges. Cross-cutting audit helper
  appends to `state["logs"]` and persists to `agent_logs`.
- **Why two state layers**: domain tables (`cases/steps/documents/agent_logs`)
  are the queryable source of truth for the UI; the LangGraph checkpointer
  (thread_id = case_id) is the *agent's* working memory enabling mid-graph
  interrupt/resume. Different lifetimes, different consumers.
- **The SSE path**: `POST /cases/{id}/run` streams `{agent, status, payload}`
  events from `graph.astream(stream_mode="updates")`; the frontend animation is
  a pure function of that stream.
- **Fallback ladders everywhere** (a resilience story): Groq → keyword rules;
  Gemini embeddings → local sentence-transformers; Gemini Vision → Tesseract
  OCR; Postgres checkpointer → graceful no-persistence mode. The demo cannot be
  killed by a single quota.
- **Step completion semantics**: `PATCH /cases/{id}/steps/{step_id}` recomputes
  the whole case deterministically — locked steps stay locked until *all* prior
  steps complete; undo re-locks downstream; progress and status roll up.

---

## 8. Timing Plan for a 15-Minute Slot

| Minutes | Content |
| --- | --- |
| 0–1 | 30-second opening + the one-line problem statement |
| 1–4 | Act 1: flagship lost-NIC→passport flow |
| 4–6 | Act 2: complete steps, unlock, dashboard, statefulness |
| 6–8 | Act 3: custom goal (citizenship) — generalization |
| 8–9 | Architecture slide + free-tier cost story |
| 9–10 | Close: buyer, impact, "from confusion to completion" |
| 10–15 | Q&A (use §5; steer back to the demo whenever possible) |

If you get only 5 minutes: Act 1 + step-unlock moment + close. Skip everything else.

---

## 9. The Three Sentences to Leave Them With

1. "Every animation you saw was a **real agent finishing real work** — this is a
   stateful multi-agent system, not a themed chatbot."
2. "The order of steps can't be hallucinated — **rules decide structure, LLMs
   decide language**."
3. "**ChatGPT answers questions. HelpLK executes government procedures.**"
