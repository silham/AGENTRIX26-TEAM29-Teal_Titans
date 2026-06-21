"""Owner: M5. Form Assistant LangGraph node.

Uses Groq (Llama 3.3 70B via M2's groq_client) to:
- Explain confusing government form fields in plain language
- Validate a citizen's filled-in form data and flag issues

State keys consumed:  (none — invoked directly via API, not wired to main graph flow)
State keys returned:  {} (form assist is request/response, not graph-stateful)
"""

from __future__ import annotations

import json
import logging

from app.graph.state import GraphState
from app.llm import groq_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language helpers
# ---------------------------------------------------------------------------

_LANG_NAMES = {"en": "English", "si": "Sinhala", "ta": "Tamil"}


def _lang_name(code: str) -> str:
    return _LANG_NAMES.get(code, "English")


# ---------------------------------------------------------------------------
# Field explanation
# ---------------------------------------------------------------------------

_EXPLAIN_SYSTEM = (
    "You are a helpful Sri Lankan government services assistant. "
    "Explain government form fields in simple, plain language that any citizen can understand. "
    "Always respond in valid JSON."
)


def explain_fields(
    form_name: str,
    fields: list[str],
    language: str = "en",
) -> list[dict]:
    """
    Ask Groq to explain each form field.

    Returns a list of dicts: [{field, explanation, example}, ...]
    """
    lang = _lang_name(language)
    user_msg = (
        f"Form name: {form_name}\n"
        f"Fields to explain: {json.dumps(fields)}\n"
        f"Response language: {lang}\n\n"
        "Return a JSON array where each element has exactly these keys:\n"
        '  "field": <string>,\n'
        '  "explanation": <plain-language explanation in the requested language>,\n'
        '  "example": <example value or null>\n'
        "Return ONLY the JSON array, no markdown, no extra text."
    )

    try:
        raw = groq_client.chat(
            [
                {"role": "system", "content": _EXPLAIN_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            json_mode=False,
        )
        # Strip possible markdown fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(l for l in cleaned.splitlines() if not l.startswith("```"))
        explanations = json.loads(cleaned)
        if isinstance(explanations, list):
            return explanations
    except Exception as exc:
        logger.error("explain_fields Groq call failed: %s", exc)

    # Fallback: return empty explanations with error note
    return [
        {"field": f, "explanation": "Explanation unavailable — please try again.", "example": None}
        for f in fields
    ]


# ---------------------------------------------------------------------------
# Form validation
# ---------------------------------------------------------------------------

_VALIDATE_SYSTEM = (
    "You are a Sri Lankan government form validation assistant. "
    "Check the citizen's answers for missing, invalid, or incorrect field values. "
    "Always respond in valid JSON."
)


def validate_form(
    form_name: str,
    filled_data: dict,
    language: str = "en",
) -> dict:
    """
    Ask Groq to validate filled form data.

    Returns: {is_valid, issues: [{field, issue, suggestion}], summary}
    """
    lang = _lang_name(language)
    user_msg = (
        f"Form name: {form_name}\n"
        f"Filled data: {json.dumps(filled_data, ensure_ascii=False)}\n"
        f"Response language: {lang}\n\n"
        "Validate each field for correctness (format, completeness, Sri Lankan conventions).\n"
        "Return a JSON object with exactly these keys:\n"
        '  "is_valid": <boolean>,\n'
        '  "issues": [{"field": ..., "issue": ..., "suggestion": ...}],\n'
        '  "summary": <one sentence summary in the requested language>\n'
        "Return ONLY the JSON object, no markdown, no extra text."
    )

    try:
        raw = groq_client.chat(
            [
                {"role": "system", "content": _VALIDATE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            json_mode=True,
        )
        result = json.loads(raw)
        return result
    except Exception as exc:
        logger.error("validate_form Groq call failed: %s", exc)
        return {
            "is_valid": False,
            "issues": [],
            "summary": "Validation service temporarily unavailable. Please try again.",
        }


# ---------------------------------------------------------------------------
# LangGraph node (passthrough — form assist is request/response via API)
# ---------------------------------------------------------------------------


def form(state: GraphState) -> dict:
    """
    Form Assistant node.
    Form assist is synchronous request/response (via /forms/explain and /forms/validate),
    not a graph-traversal step, so this node is a no-op pass-through in the graph.
    """
    return {}
