"""Translate a CaseDetail on its way out of the API.

The response DTO is the ONLY place output translation happens. Nothing is
written back, so switching language is a pure read-path change: no graph
re-run, no `replace_steps` DELETE+INSERT, no lost step completions.

Two field sets, because the two endpoints show very different amounts of text:
the dashboard card renders three strings per case while `GET /cases` serialises
full steps, requirements and citations. Translating uniformly would spend ~40x
the tokens the screen actually displays.
"""
from __future__ import annotations

from app.i18n.glossary import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from app.i18n.translator import translate_many
from app.schemas.case import CaseDetail

# What the dashboard actually renders (CaseCard: parent goal, goal, next step).
LIST_FIELDS: frozenset[str] = frozenset({"goal", "step_title", "parent_goal"})

# Everything visible on the case detail screen.
DETAIL_FIELDS: frozenset[str] = frozenset(
    {
        "goal",
        "parent_goal",
        "step_title",
        "step_description",
        "step_reason",
        "requirement_name",
        "requirement_issues",
        "citation_title",
        "citation_snippet",
        "subgoal_goal",
    }
)


def _collect(detail: CaseDetail, fields: frozenset[str]) -> list[str]:
    out: list[str] = []

    # A citizen's own words are shown back verbatim: they typed them, and
    # round-tripping their Sinhala through English would hand back something
    # they did not write. Only machine-written goals (sub-goals, which are
    # generated in English) are translated.
    if "goal" in fields and detail.goal_source == "generated":
        out.append(detail.goal)
    if "parent_goal" in fields and detail.parent is not None:
        out.append(detail.parent.goal)

    for step in detail.steps:
        if "step_title" in fields:
            out.append(step.title)
        if "step_description" in fields and step.description:
            out.append(step.description)
        if "step_reason" in fields and step.reason:
            out.append(step.reason)

    for doc in detail.documents:
        if "requirement_name" in fields:
            out.append(doc.name)
        if "requirement_issues" in fields:
            out.extend(i for i in doc.issues if isinstance(i, str))

    for cite in detail.citations:
        if "citation_title" in fields:
            out.append(cite.title)
        if "citation_snippet" in fields and cite.snippet:
            out.append(cite.snippet)

    for sub in detail.sub_goals:
        if "subgoal_goal" in fields:
            out.append(sub.goal)

    return out


def _apply(detail: CaseDetail, mapping: dict[str, str], fields: frozenset[str]) -> None:
    def tr(value: str) -> str:
        return mapping.get(value, value)

    if "goal" in fields and detail.goal_source == "generated":
        detail.goal = tr(detail.goal)
    if "parent_goal" in fields and detail.parent is not None:
        detail.parent.goal = tr(detail.parent.goal)

    for step in detail.steps:
        if "step_title" in fields:
            step.title = tr(step.title)
        if "step_description" in fields and step.description:
            step.description = tr(step.description)
        if "step_reason" in fields and step.reason:
            step.reason = tr(step.reason)

    for doc in detail.documents:
        if "requirement_name" in fields:
            doc.name = tr(doc.name)
        if "requirement_issues" in fields:
            doc.issues = [tr(i) if isinstance(i, str) else i for i in doc.issues]

    for cite in detail.citations:
        if "citation_title" in fields:
            cite.title = tr(cite.title)
        if "citation_snippet" in fields and cite.snippet:
            cite.snippet = tr(cite.snippet)

    for sub in detail.sub_goals:
        if "subgoal_goal" in fields:
            sub.goal = tr(sub.goal)


def localize_case(
    detail: CaseDetail,
    lang: str,
    *,
    fields: frozenset[str] = DETAIL_FIELDS,
    cache_only: bool = False,
) -> CaseDetail:
    """Return `detail` with its citizen-facing strings in `lang`.

    Mutates and returns the same object: it was built for this response by
    `model_validate` and is not shared, so a copy would be waste. Do NOT pass
    an ORM-attached model here.

    One batched translation call per response, never one per field.
    """
    if lang == DEFAULT_LANGUAGE or lang not in SUPPORTED_LANGUAGES:
        return detail

    texts = _collect(detail, fields)
    if not texts:
        return detail

    mapping = translate_many(texts, lang, cache_only=cache_only)
    _apply(detail, mapping, fields)
    return detail


def localize_cases(
    details: list[CaseDetail],
    lang: str,
    *,
    fields: frozenset[str] = LIST_FIELDS,
    cache_only: bool = True,
) -> list[CaseDetail]:
    """Localize a whole list in ONE translation pass.

    Per-case calls would issue N round trips for a dashboard of N plans;
    collecting first means one batch for the entire page.
    """
    if lang == DEFAULT_LANGUAGE or lang not in SUPPORTED_LANGUAGES or not details:
        return details

    texts = [t for d in details for t in _collect(d, fields)]
    if not texts:
        return details

    mapping = translate_many(texts, lang, cache_only=cache_only)
    for detail in details:
        _apply(detail, mapping, fields)
    return details
