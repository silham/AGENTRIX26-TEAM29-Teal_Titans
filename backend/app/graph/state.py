"""Owner: M2. Shared state passed between all LangGraph nodes. SHARED CONTRACT.

Each node is `def node(state: GraphState) -> dict` returning a PARTIAL update
(LangGraph merges it). Add keys here (with M2) rather than inventing ad-hoc ones.
"""
from __future__ import annotations

from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    # Identity / context
    case_id: str
    user_id: str
    language: str

    # Planner (M2)
    goal: str
    detected_services: list[str]
    intent: dict[str, Any]

    # Knowledge / RAG (M3)
    requirements: list[str]
    citations: list[dict[str, Any]]
    # Knowledge-base passages retrieved by the planner, reused by the knowledge
    # node so a run embeds the goal once rather than twice.
    retrieved_passages: list[dict[str, Any]]

    # Dependency (M3)
    dependency_graph: dict[str, Any]

    # Eligibility (M4)
    eligibility: dict[str, Any]
    questions: list[str]
    # Structured clarifying questions the UI can render as inputs:
    # [{field, question, type: choice|boolean|number|text, options?}, ...]
    question_fields: list[dict[str, Any]]
    # Citizen's answers, injected on resume via graph.aupdate_state
    facts: dict[str, Any]
    # Alternate routes for blocked services: [{service, reason, alternative}, ...]
    alternatives: list[dict[str, Any]]
    # True when a checkpointer is active, i.e. the graph CAN pause to ask the
    # user; without one the eligibility Q&A loop is skipped (non-blocking)
    interactive: bool

    # Checklist (M4)
    checklist: list[dict[str, Any]]
    progress: int

    # Documents (M5)
    documents: list[dict[str, Any]]

    # LLM-generated steps + requirements for goals with no matching procedure JSON (M2)
    custom_steps: list[dict[str, Any]]
    custom_requirements: list[str]

    # Reminder (M4)
    reminders: list[dict[str, Any]]

    # Conversation / audit
    messages: list[dict[str, Any]]
    logs: list[dict[str, Any]]
