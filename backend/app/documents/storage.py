"""Owner: M5. Private file storage layer for citizen document uploads.

Storage backend: local filesystem for the hackathon (swap for Supabase Storage
or Cloudflare R2 with signed URLs in production).

All files are stored under settings.storage_dir/{case_id}/ and are never
directly accessible — served only via backend endpoints after user_id check.
"""

from __future__ import annotations

import logging
import mimetypes
import uuid
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class StorageConfigError(Exception):
    """Raised when required storage config is missing."""


class StorageUploadError(Exception):
    """Raised when upload fails."""


class StorageDeleteError(Exception):
    """Raised when delete fails."""


class StorageSignedUrlError(Exception):
    """Raised when generating a URL fails."""


# ---------------------------------------------------------------------------
# Path builder
# ---------------------------------------------------------------------------


def build_storage_path(user_id: str, case_id: str, original_filename: str) -> str:
    """
    Construct a deterministic, collision-safe storage path.

    Structure: {user_id}/{case_id}/{uuid8}_{sanitised_filename}
    """
    safe_name = "".join(
        c if c.isalnum() or c in "._-" else "_" for c in original_filename
    ).lower()
    unique_prefix = str(uuid.uuid4())[:8]
    return f"{user_id}/{case_id}/{unique_prefix}_{safe_name}"


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


async def upload_file(
    file_bytes: bytes,
    original_filename: str,
    user_id: str,
    case_id: str,
) -> str:
    """
    Save file_bytes to private local storage and return the storage path.

    In production: swap body for Supabase client.storage.from_(bucket).upload(...)
    """
    storage_path = build_storage_path(user_id, case_id, original_filename)
    abs_path = Path(settings.storage_dir) / storage_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        abs_path.write_bytes(file_bytes)
    except Exception as exc:
        raise StorageUploadError(f"Failed to write file to {abs_path}: {exc}") from exc

    logger.info("Uploaded: %s (%d bytes)", storage_path, len(file_bytes))
    return storage_path


# ---------------------------------------------------------------------------
# Read back
# ---------------------------------------------------------------------------


class StorageReadError(Exception):
    """Raised when a stored file cannot be read back."""


def read_file(storage_path: str) -> bytes:
    """Return the bytes of a previously stored file.

    Used by the knowledge-base ingestion worker, which re-reads the upload after
    the request that stored it has already returned.
    """
    abs_path = Path(settings.storage_dir) / storage_path
    try:
        return abs_path.read_bytes()
    except FileNotFoundError as exc:
        raise StorageReadError(f"Stored file is missing: {storage_path}") from exc
    except Exception as exc:
        raise StorageReadError(f"Failed to read {storage_path}: {exc}") from exc


# ---------------------------------------------------------------------------
# Signed URL (local → direct path; Supabase in production)
# ---------------------------------------------------------------------------


async def get_signed_url(storage_path: str, expires_in: int = 3600) -> str:
    """
    Return a URL for serving the file.
    For local dev this is just the absolute path; swap for Supabase signed URL in prod.
    """
    abs_path = Path(settings.storage_dir) / storage_path
    if not abs_path.exists():
        raise StorageSignedUrlError(f"File not found: {storage_path}")
    # In production: return supabase.storage.from_(bucket).create_signed_url(...)["signedURL"]
    return f"file://{abs_path.as_posix()}"


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


async def delete_file(storage_path: str) -> None:
    """
    Permanently remove a file. Called ONLY after ownership is verified in the repo layer.
    """
    abs_path = Path(settings.storage_dir) / storage_path
    try:
        if abs_path.exists():
            abs_path.unlink()
            logger.info("Deleted: %s", storage_path)
        else:
            logger.warning("delete_file: path not found (already deleted?): %s", storage_path)
    except Exception as exc:
        raise StorageDeleteError(f"Failed to delete {storage_path}: {exc}") from exc


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def check_storage_health() -> dict[str, str]:
    """Verify that the storage directory is writable (called by /health endpoint)."""
    try:
        base = Path(settings.storage_dir)
        base.mkdir(parents=True, exist_ok=True)
        test_file = base / ".health_check"
        test_file.write_text("ok")
        test_file.unlink()
        return {"storage": "ok", "dir": str(base)}
    except Exception as exc:
        return {"storage": "error", "detail": str(exc)}


# Convenience alias used by scaffold
def save(case_id: str, filename: str, data: bytes) -> str:
    """Synchronous save — used by scaffold integration tests."""
    base = Path(settings.storage_dir) / case_id
    base.mkdir(parents=True, exist_ok=True)
    path = base / filename
    path.write_bytes(data)
    return str(path)
