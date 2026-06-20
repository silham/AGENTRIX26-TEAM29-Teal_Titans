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

    # Dependency (M3)
    dependency_graph: dict[str, Any]

    # Eligibility (M4)
    eligibility: dict[str, Any]
    questions: list[str]

    # Checklist (M4)
    checklist: list[dict[str, Any]]
    progress: int

    # Documents (M5)
    documents: list[dict[str, Any]]

    # Reminder (M4)
    reminders: list[dict[str, Any]]

    # Conversation / audit
    messages: list[dict[str, Any]]
    logs: list[dict[str, Any]]
