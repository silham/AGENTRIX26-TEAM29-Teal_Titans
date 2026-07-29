"""Per-request render language.

Read from a header rather than `case.language` because the two mean different
things: `case.language` records what the citizen WROTE, while the header
carries what they want to READ. A citizen can switch language at any time
without that touching a single stored row.
"""
from __future__ import annotations

# pyrefly: ignore [missing-import]
from fastapi import Header

from app.i18n.glossary import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES


def request_language(x_language: str | None = Header(default=None)) -> str:
    """Validated language for this response, defaulting to English.

    Anything unrecognised — a missing header, "fr", an injection attempt —
    falls back to English rather than erroring. A bad language header is never
    a reason to deny a citizen their plan.
    """
    if not x_language:
        return DEFAULT_LANGUAGE
    candidate = x_language.strip().lower()[:8]
    return candidate if candidate in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
