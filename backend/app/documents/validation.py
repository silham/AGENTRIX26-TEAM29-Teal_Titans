"""Owner: M6. Shared upload guards for every multipart endpoint.

Applied to both the citizen document upload and the admin knowledge-base upload,
neither of which previously had a size cap or a type allowlist.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings
from app.rag.extract import EXT_KIND

READ_CHUNK = 1 << 20  # 1 MiB


def max_upload_bytes() -> int:
    return settings.max_knowledge_upload_mb * 1024 * 1024


async def read_capped(file: UploadFile, max_bytes: int | None = None) -> bytes:
    """Read an upload with a hard size ceiling.

    ``await file.read()`` with no argument buffers the ENTIRE body into memory
    before any check can run, so a 2 GB request is accepted and then rejected —
    too late. Reading in bounded chunks lets us reject as soon as the cap trips.
    """
    limit = max_upload_bytes() if max_bytes is None else max_bytes
    buffer = bytearray()
    total = 0
    while True:
        chunk = await file.read(READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {limit // 1024 // 1024} MB upload limit.",
            )
        buffer.extend(chunk)

    if not buffer:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    return bytes(buffer)


def validate_extension(filename: str | None, allowed: dict[str, str] | None = None) -> str:
    """Reject unsupported file types by extension. Returns the lowercased extension.

    The extension is authoritative, not Content-Type: browsers routinely send
    ``application/octet-stream`` for .md and .docx.
    """
    table = EXT_KIND if allowed is None else allowed
    ext = Path(filename or "").suffix.lower()
    if ext not in table:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{ext or filename or 'unknown'}'. "
                f"Allowed: {', '.join(sorted(table))}"
            ),
        )
    return ext
