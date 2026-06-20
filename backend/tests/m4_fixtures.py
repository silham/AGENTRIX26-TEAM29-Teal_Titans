"""Shared M4 test fixtures: the "lost NIC → passport" demo GraphState pieces.

Hand-built so M4's nodes can be unit-tested without M3's real rules/RAG data.
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
    """Passport is locked behind a valid NIC; duplicate NIC is open."""
    return {
        "order": ["duplicate_nic", "passport_application"],
        "services": {
            "duplicate_nic": {
                "name": "Duplicate NIC Application",
                "blocked": False,
                "reason": None,
                "depends_on": [],
                "source_url": "https://www.drp.gov.lk",
                "steps": [
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
            },
            "passport_application": {
                "name": "Passport Application",
                "blocked": True,
                "reason": "Valid NIC required",
                "depends_on": ["valid_nic"],
                "source_url": "https://www.immigration.gov.lk",
                "steps": [
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
            },
        },
    }


def eligibility_eligible() -> dict:
    return {
        "overall": "eligible",
        "services": {
            "duplicate_nic": {"verdict": "eligible", "blockers": [], "missing_facts": []},
            "passport_application": {"verdict": "eligible", "blockers": [], "missing_facts": []},
        },
    }
