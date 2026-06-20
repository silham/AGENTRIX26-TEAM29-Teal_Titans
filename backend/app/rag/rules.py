"""Owner: M3. Load + query the deterministic rules layer (data/procedures/*.json).

This layer is intentionally NOT LLM-driven. Dependency, eligibility, and step
locking come from these JSON files so the demo behaves reliably and is auditable.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

PROCEDURES_DIR = Path(__file__).resolve().parents[2] / "data" / "procedures"


@lru_cache(maxsize=1)
def load_procedures() -> dict[str, dict]:
    """Load every procedure JSON, keyed by its ``id``. Cached after first read."""
    out: dict[str, dict] = {}
    for f in sorted(PROCEDURES_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        out[data["id"]] = data
    return out


def get_procedure(service: str) -> dict | None:
    """Return the full procedure record for ``service`` (its id), or None."""
    return load_procedures().get(service)


def requirements(service: str) -> list[str]:
    """Required documents/inputs for a service (e.g. ['valid_nic', ...])."""
    proc = get_procedure(service)
    return list(proc.get("requirements", [])) if proc else []


def depends_on(service: str) -> list[str]:
    """Service ids this service depends on (prerequisite procedures)."""
    proc = get_procedure(service)
    return list(proc.get("depends_on", [])) if proc else []


def dependency_conditions(service: str) -> list[dict[str, Any]]:
    """Conditional dependencies: when a requirement is missing, which prerequisite
    service unlocks it and why. Shape: [{service, when_missing, reason}, ...]."""
    proc = get_procedure(service)
    return list(proc.get("dependency_conditions", [])) if proc else []


def eligibility_rules(service: str) -> list[dict[str, Any]]:
    """Deterministic eligibility predicates for a service."""
    proc = get_procedure(service)
    return list(proc.get("eligibility_rules", [])) if proc else []


def steps(service: str) -> list[dict[str, Any]]:
    """Ordered steps for a service (each: title, description, source_url)."""
    proc = get_procedure(service)
    return list(proc.get("steps", [])) if proc else []


def source_url(service: str) -> str | None:
    """Canonical source URL for a service."""
    proc = get_procedure(service)
    return proc.get("source_url") if proc else None


def name(service: str) -> str:
    """Human-readable service name; falls back to the id."""
    proc = get_procedure(service)
    return proc.get("name", service) if proc else service
