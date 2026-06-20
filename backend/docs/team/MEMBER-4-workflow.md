# M4 — Eligibility, Checklist & Reminder

**Branch:** `feat/be-m4-workflow`
**You turn knowledge + dependencies into the citizen's actionable plan** — the
ordered checklist, progress, eligibility gating, and nudges the dashboard shows.

## Files you own

```
app/graph/nodes/eligibility.py   Eligibility node (rules + Groq)
app/graph/nodes/checklist.py     Checklist + progress composition
app/graph/nodes/reminder.py      Reminder / next-best-action logic
tests/test_m4_*.py
```

## Responsibilities

1. **Eligibility node (`nodes/eligibility.py`).** Read `eligibility_rules` from
   the rules layer (via state populated by M3) plus the user's known facts.
   Decide eligible / blocked, and produce the **minimal** set of clarifying
   questions (use M2's `groq_client` for phrasing only — the *decision* stays
   rule-based). Write `eligibility` into `GraphState`; flag blockers.
2. **Checklist node (`nodes/checklist.py`).** Combine requirements (M3) +
   dependency order/locks (M3) + eligibility (you) into an **ordered** task list
   with statuses (`pending / active / completed / locked`). Compute the
   **progress %** and the single **next best action**. Persist steps via M1's
   `repositories/steps.py`.
3. **Reminder node (`nodes/reminder.py`).** Derive nudges: upcoming appointment,
   document expiry, inactive step (e.g. ">7 days"), still-missing uploads. Return
   a list of reminder items for the dashboard.

## Contracts you consume

- `GraphState` keys (M2) — read `requirements`, `dependency_graph`; write
  `eligibility`, `checklist`.
- `groq_client` (M2) — eligibility question phrasing only.
- `repositories/steps.py` + `db/models.py` (M1) — persist computed steps.
- Rules schema fields (M3) — `eligibility_rules`, `depends_on`.

## Definition of done

- Given requirements + a locked dependency, the checklist orders steps correctly,
  keeps the blocked step `locked`, and reports an accurate progress %.
- Eligibility returns a clear verdict + only the necessary follow-up questions.
- Reminder produces sensible nudges from step/document state.

> Tip: your three nodes are independent files — you can build and unit-test each
> against a hand-written `GraphState` fixture without waiting on M3's real data.
