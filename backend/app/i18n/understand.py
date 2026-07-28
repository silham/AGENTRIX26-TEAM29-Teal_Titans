"""Normalise citizen input to English, once, at the request boundary.

Citizens write in whatever way is natural to them, and all of these must reach
the same plan:

    "I lost my NIC"                     pure English
    "මගේ ජාතික හැඳුනුම්පත නැති වුණා"    pure Sinhala script
    "mata NIC eka nathi una"            Singlish (romanised Sinhala)
    "en NIC card tholainthuduchu"       Tanglish (romanised Tamil)
    "මට passport එකක් ඕන"               mixed script

Everything downstream — service detection, the RAG query, the eligibility
rules, the English-only keyword fallback — then operates on English, which is
what lets the existing English corpus and English-tuned score floor keep
working untouched. The citizen's original wording is preserved separately on
`Case.goal` and shown back to them verbatim.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.config import settings
from app.i18n.glossary import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from app.llm import groq_client

logger = logging.getLogger(__name__)

# Unicode blocks. Presence of either is conclusive — no model call needed to
# know the script, only to translate it.
_SINHALA = range(0x0D80, 0x0E00)
_TAMIL = range(0x0B80, 0x0C00)


@dataclass(frozen=True)
class InputAnalysis:
    """Result of normalising one piece of citizen text."""

    english: str
    detected_language: str  # "en" | "si" | "ta"
    script: str             # "latin" | "sinhala" | "tamil" | "mixed"
    used_llm: bool = False


def detect_script(text: str) -> str:
    has_si = any(ord(c) in _SINHALA for c in text)
    has_ta = any(ord(c) in _TAMIL for c in text)
    has_latin = any(c.isascii() and c.isalpha() for c in text)

    if has_si and has_ta:
        return "mixed"
    if has_si:
        return "mixed" if has_latin else "sinhala"
    if has_ta:
        return "mixed" if has_latin else "tamil"
    return "latin"


# Romanised-Sinhala/Tamil markers that plain English never contains. Used only
# to decide whether the ASCII fast path is safe — never to translate.
_TRANSLITERATION_HINTS = frozenset(
    {
        # Sinhala
        "mata", "mage", "eka", "ekak", "ona", "oni", "onane", "nathi", "naha",
        "karanna", "kohomada", "puluwan", "avashya", "denna", "gannawa",
        "ganna", "hadanna", "yanna", "thiyenawa", "wenawa", "una", "unaa",
        # Tamil
        "enakku", "ennoda", "vendum", "venum", "epdi", "eppadi", "irukku",
        "pannanum", "kudukkanum", "thevai", "illai", "tholainthu", "seiya",
    }
)

_SYSTEM = (
    "You normalise how Sri Lankan citizens describe a government service need "
    "into plain English, so a rules engine can match it.\n"
    "Input may be English, Sinhala or Tamil script, romanised Sinhala "
    "(Singlish, e.g. 'mata passport ekak ona'), romanised Tamil (Tanglish), or "
    "any mixture of these in one sentence.\n"
    "Reply ONLY with JSON: "
    '{"language": "en|si|ta", "english": "<the request in plain English>"}\n'
    "Rules:\n"
    "- 'language' is the language the citizen WROTE IN. For romanised Sinhala "
    "answer 'si' and for romanised Tamil answer 'ta', even though the letters "
    "are Latin. Use 'en' only for genuine English.\n"
    "- For mixed input, report the language of the majority of the meaning.\n"
    "- 'english' must be first person, one sentence, and must preserve every "
    "detail: which document, whether it was lost/stolen/expired, any deadline.\n"
    "- Do not answer the request, offer advice, or add anything not stated."
)


def _fast_path(text: str) -> InputAnalysis | None:
    """Recognise plain English without spending a model call.

    Matters more than it looks: every landing-page shortcut and every example
    chip is already English, so this covers the most-travelled path in the app
    and makes those flows deterministic and testable offline.

    Deliberately conservative — ASCII alone is NOT enough, because Singlish is
    also ASCII. A transliteration marker sends it to the model.
    """
    stripped = text.strip()
    if not stripped.isascii():
        return None

    words = {w.strip(".,!?;:'\"").lower() for w in stripped.split()}
    if words & _TRANSLITERATION_HINTS:
        return None

    return InputAnalysis(english=stripped, detected_language="en", script="latin")


def _parse(raw: str, original: str) -> InputAnalysis:
    data = json.loads(raw)
    english = str(data.get("english") or "").strip()
    lang = str(data.get("language") or DEFAULT_LANGUAGE).strip().lower()

    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    if not english:
        english = original

    return InputAnalysis(
        english=english,
        detected_language=lang,
        script=detect_script(original),
        used_llm=True,
    )


def _fallback(text: str) -> InputAnalysis:
    """What to return when normalisation is unavailable.

    English + the original text, i.e. exactly what the system did before this
    module existed. A Groq outage therefore degrades the product to its
    previous behaviour instead of failing the request.
    """
    return InputAnalysis(
        english=text.strip(),
        detected_language=DEFAULT_LANGUAGE,
        script=detect_script(text),
    )


def normalize_input(text: str) -> InputAnalysis:
    """Sync variant, for use from `def` endpoints (FastAPI's threadpool)."""
    fast = _fast_path(text)
    if fast is not None:
        return fast
    if not settings.groq_api_key:
        return _fallback(text)
    try:
        raw = groq_client.chat(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": text.strip()},
            ],
            json_mode=True,
        )
        return _parse(raw, text)
    except Exception:
        logger.warning("input normalisation failed; using text as-is", exc_info=True)
        return _fallback(text)


async def normalize_input_async(text: str) -> InputAnalysis:
    """Async variant, for `async def` endpoints.

    Separate rather than wrapping the sync one in a thread because Groq ships a
    real async client — and calling the blocking one from the event loop would
    stall every other request for the duration of up to three retries.
    """
    fast = _fast_path(text)
    if fast is not None:
        return fast
    if not settings.groq_api_key:
        return _fallback(text)
    try:
        raw = await groq_client.chat_async(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": text.strip()},
            ],
            json_mode=True,
        )
        return _parse(raw, text)
    except Exception:
        logger.warning("input normalisation failed; using text as-is", exc_info=True)
        return _fallback(text)
