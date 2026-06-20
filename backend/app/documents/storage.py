"""Owner: M5. Private file storage. Local-dir fallback for the hackathon; swap for
Supabase Storage / Cloudflare R2 with signed URLs in production."""
from pathlib import Path

from app.config import settings


def save(case_id: str, filename: str, data: bytes) -> str:
    base = Path(settings.storage_dir) / case_id
    base.mkdir(parents=True, exist_ok=True)
    path = base / filename
    path.write_bytes(data)
    return str(path)


# TODO(M5): signed_url(path), delete(path); move to a private bucket.
