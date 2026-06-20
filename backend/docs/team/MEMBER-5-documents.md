# M5 — Documents & Forms

**Branch:** `feat/be-m5-documents`
**You own everything about uploaded files and form assistance** — storage, vision
validation, and the form helper. Self-contained domain with its own API + nodes.

## Files you own

```
app/documents/storage.py         private bucket upload + signed URL
app/documents/ocr.py             Tesseract fallback
app/llm/gemini_vision.py         Gemini 1.5 Flash vision wrapper
app/graph/nodes/document.py      Document Verification node
app/graph/nodes/form.py          Form Assistant node
app/api/documents.py             upload / verify / delete endpoints
app/api/forms.py                 form-assist endpoints
app/repositories/documents.py    document persistence
app/schemas/document.py          document DTOs
tests/test_m5_*.py
```

## Responsibilities

1. **Storage (`documents/storage.py`).** Upload to a **private** bucket
   (Supabase Storage / Cloudflare R2). Files are reachable only via an authorized
   backend endpoint that checks `user_id` (data-safety requirement). Provide
   signed URLs for short-lived access.
2. **Vision (`llm/gemini_vision.py`) + OCR (`documents/ocr.py`).** Gemini Vision
   reads the upload; Tesseract is the **zero-quota fallback**. Extract type +
   visible fields.
3. **Document Verification node (`nodes/document.py`).** Detect document type,
   check required fields/signatures/readability, set status
   (`accepted / rejected / incomplete / needs_verification`) with an `issues`
   list. Update the document row and reflect into `GraphState`.
4. **Form Assistant node (`nodes/form.py`).** Explain fields, flag missing/unsigned
   sections, validate formats (uses M2's `groq_client`). Returns explanations +
   validation results — no real form submission (mock per the MVP non-goals).
5. **APIs (`api/documents.py`, `api/forms.py`).** `POST /documents` (upload →
   verify), `GET /documents/{id}`, `DELETE /documents/{id}` (citizen can erase
   their data), `POST /forms/explain`, `POST /forms/validate`. Protect all routes
   with M1's `get_current_user`.

## Contracts you consume

- `get_current_user`, `get_db`, `db/models.py` `documents` (M1).
- `GraphState` keys + `groq_client` (M2).

## Definition of done

- Upload a passport-photo / form image → stored privately → returns a verdict with
  issues; checklist reflects the new document status.
- `DELETE /documents/{id}` removes the file and row for the owning user only.
- Form explain/validate returns useful field-level guidance.

> Tip: your domain barely overlaps the graph — you can develop the upload→verify
> API loop and the Gemini wrapper independently, then drop results into your two
> node stubs.
