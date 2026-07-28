"""Owner: M3. Corpus ingestion CLI: chunk -> embed -> write doc_chunks.

Usage:
    python -m app.rag.ingest

Reads every ``*.txt`` file under ``data/corpus/``. Each file starts with header
lines (``source_url:`` and ``title:``) followed by a blank line and the body. The
body is split into overlapping chunks, embedded via ``app.llm.embeddings``
(Gemini with a local fallback), and written to the ``doc_chunks`` table with
their source URL for citations.

Each corpus file also gets a ``knowledge_documents`` row (uploaded_by =
"corpus-cli"), so seeded documents and admin uploads are the same kind of thing
and both appear in /admin/knowledge. The actual chunk/embed/store work lives in
app.rag.pipeline, shared with the upload path.

Idempotent: existing chunks for each document are deleted before re-inserting,
so the command can be re-run safely.
"""
from __future__ import annotations

from pathlib import Path

from app.db.session import SessionLocal
from app.rag import pipeline
from app.repositories import knowledge as knowledge_repo

CORPUS_DIR = Path(__file__).resolve().parents[2] / "data" / "corpus"

CHUNK_SIZE = 800  # characters
CHUNK_OVERLAP = 120


def parse_corpus_file(path: Path) -> tuple[str | None, str | None, str]:
    """Return (source_url, title, body) from a corpus .txt file.

    Header lines ``key: value`` precede a blank line; everything after is the body.
    Files without headers are treated as all-body with no metadata.
    """
    text = path.read_text(encoding="utf-8")
    source_url: str | None = None
    title: str | None = None

    lines = text.splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "":
            body_start = i + 1
            break
        if stripped.lower().startswith("source_url:"):
            source_url = stripped.split(":", 1)[1].strip()
        elif stripped.lower().startswith("title:"):
            title = stripped.split(":", 1)[1].strip()
        else:
            # First non-header, non-blank line => no header block; body is whole file.
            body_start = 0
            break

    body = "\n".join(lines[body_start:]).strip() if body_start else text.strip()
    return source_url, title, body


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping character windows, preferring paragraph breaks."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        # Try to end on a paragraph or sentence boundary for cleaner chunks.
        if end < n:
            window = text[start:end]
            for sep in ("\n\n", "\n", ". "):
                idx = window.rfind(sep)
                if idx >= size // 2:
                    end = start + idx + len(sep)
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def ingest() -> int:
    """Ingest the corpus into doc_chunks. Returns the number of chunks written."""
    files = sorted(CORPUS_DIR.glob("*.txt"))
    if not files:
        print(f"[ingest] No .txt files found in {CORPUS_DIR}.")
        return 0

    total_chunks = 0
    with SessionLocal() as db:
        for path in files:
            source_url, title, body = parse_corpus_file(path)
            if not body.strip():
                print(f"[ingest] {path.name}: empty, skipped.")
                continue

            # One knowledge_documents row per corpus file, reused across re-runs
            # so the CLI stays idempotent and the row keeps its id.
            doc = knowledge_repo.find_by_filename(db, filename=path.name)
            if doc is None:
                doc = knowledge_repo.create_document(
                    db,
                    filename=path.name,
                    uploaded_by="corpus-cli",
                    title=title,
                    source_url=source_url,
                    mime="text/plain",
                    size_bytes=len(body.encode("utf-8")),
                    status="processing",
                )

            count, model_id = pipeline.store_document_chunks(
                db,
                document_id=doc.id,
                source_url=source_url,
                title=title,
                text=body,
            )
            db.commit()

            knowledge_repo.set_status(
                db,
                document_id=doc.id,
                status="ready",
                error=None,
                title=title,
                source_url=source_url,
                chunk_count=count,
                char_count=len(body),
                extraction_method="text",
                embedding_model=model_id,
            )

            total_chunks += count
            print(f"[ingest] {path.name}: {count} chunk(s) -> {source_url}")

    print(f"[ingest] Done. {total_chunks} chunk(s) from {len(files)} file(s).")
    return total_chunks


if __name__ == "__main__":
    ingest()
