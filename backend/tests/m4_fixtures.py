"""Shared M4 test fixtures: the "lost NIC → passport" demo GraphState pieces.

Hand-built so M4's nodes can be unit-tested without M3's real rules/RAG data.
Shapes mirror what M3's nodes actually produce (see app/graph/nodes/dependency.py
and app/rag/rules.py).
"""
from __future__ import annotations


def procedures() -> dict[str, dict]:
    """Stand-in for app.rag.rules.load_procedures() output (eligibility focus)."""
    return {
        "duplicate_nic": {
            "id": "duplicate_nic",
            "name": "Duplicate NIC Application",
            "eligibility_rules": [{"field": "citizenship", "equals": "sri_lankan"}],
        },
        "passport_application": {
            "id": "passport_application",
            "name": "Passport Application",
            "eligibility_rules": [{"field": "citizenship", "equals": "sri_lankan"}],
        },
    }


def dependency_graph() -> dict:
    """Matches M3's dependency node output: passport locked behind duplicate NIC."""
    return {
        "services": {
            "duplicate_nic": {
                "name": "Duplicate National Identity Card (NIC)",
                "depends_on": [],
                "status": "ready",
                "reason": None,
                "blocked_by": [],
            },
            "passport_application": {
                "name": "Passport Application",
                "depends_on": ["duplicate_nic"],
                "status": "locked",
                "reason": "Valid NIC required",
                "blocked_by": ["duplicate_nic"],
            },
        },
        "order": ["duplicate_nic", "passport_application"],
        "locked": ["passport_application"],
    }


def steps_by_service() -> dict[str, list[dict]]:
    """Stand-in for {sid: rules.steps(sid)} — the per-service ordered steps."""
    return {
        "duplicate_nic": [
            {
                "title": "Obtain police report",
                "description": "Get a police report for the lost NIC.",
                "source_url": "https://www.police.lk",
                "fulfills": "police_report",
            },
            {
                "title": "Apply for duplicate NIC",
                "description": "Submit the duplicate NIC application.",
                "source_url": "https://www.drp.gov.lk",
            },
        ],
        "passport_application": [
            {
                "title": "Complete passport application form",
                "description": "Fill the passport application form.",
                "source_url": "https://www.immigration.gov.lk",
            },
            {
                "title": "Submit passport application",
                "description": "Submit the form and documents.",
                "source_url": "https://www.immigration.gov.lk",
            },
        ],
    }


def eligibility_eligible() -> dict:
    return {
        "overall": "eligible",
        "services": {
            "duplicate_nic": {"verdict": "eligible", "blockers": [], "missing_facts": []},
            "passport_application": {"verdict": "eligible", "blockers": [], "missing_facts": []},
        },
    }
