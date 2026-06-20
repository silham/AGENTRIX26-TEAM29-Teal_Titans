# M3 — RAG & Knowledge

**Branch:** `feat/be-m3-rag`
**You own retrieval and the rules layer** — the hybrid RAG that gives reliable
dependencies and clickable citations.

## Files you own

```
app/rag/index.py                 LlamaIndex + pgvector index
app/rag/ingest.py                corpus ingestion CLI (chunk → embed → store)
app/rag/retriever.py             query → chunks + source URLs
app/rag/rules.py                 load & query data/procedures/*.json
app/graph/nodes/knowledge.py     RAG Knowledge node
app/graph/nodes/dependency.py    Dependency node (reads rules)
app/llm/embeddings.py            Gemini text-embedding-004 (+ local fallback)
data/procedures/*.json           the rules layer
data/corpus/                     real SL gov pages/PDFs
tests/test_m3_*.py
```

## Responsibilities

1. **Rules layer (`data/procedures/*.json` + `rules.py`).** Author JSON for the
   3 demo services — `passport_application`, `duplicate_nic`,
   `driving_license_renewal` — using the schema in
   [IMPLEMENTATION_PLAN.md §5](../../../IMPLEMENTATION_PLAN.md)
   (`requirements`, `depends_on`, `eligibility_rules`, `steps`, `source_url`).
   `rules.py` loads and queries them. This is **deterministic** — not LLM-driven.
2. **Embeddings (`llm/embeddings.py`).** Wrap Gemini `text-embedding-004` (free),
   with a local `sentence-transformers` fallback so the demo never blocks on quota.
3. **Ingestion (`rag/ingest.py`).** A CLI that chunks ~15–20 gov docs from
   `data/corpus/`, embeds them, and writes `doc_chunks` (content + embedding +
   source_url). Idempotent so it can be re-run.
4. **Retrieval (`rag/index.py`, `retriever.py`).** LlamaIndex over the pgvector
   store; return top-k chunks **with source URLs** for citations.
5. **Knowledge node (`nodes/knowledge.py`).** From detected services, gather
   requirements (from rules) + supporting passages (from retrieval), write
   `requirements` and `citations` into `GraphState`.
6. **Dependency node (`nodes/dependency.py`).** Build the dependency graph from
   `depends_on`, mark blocked steps `locked` with a reason
   (e.g. "Valid NIC required"). Pure rules → reliable.

## Contracts you consume

- `GraphState` keys (M2) — write `requirements`, `dependency_graph`, `citations`.
- `db/models.py` `doc_chunks` (M1) for the vector store.

## Definition of done

- `python -m app.rag.ingest` populates `doc_chunks` from the corpus.
- A query returns relevant passages **with working source URLs**.
- For "lost NIC → passport", the dependency node locks the passport step behind NIC.
