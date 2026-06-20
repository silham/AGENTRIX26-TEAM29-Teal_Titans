"""Owner: M3. Rules layer — the 3 demo procedures load and query correctly. No DB."""
from app.rag import rules

DEMO_SERVICES = {"passport_application", "duplicate_nic", "driving_license_renewal"}


def test_all_demo_procedures_present():
    procs = rules.load_procedures()
    assert DEMO_SERVICES.issubset(procs.keys())


def test_procedure_schema_fields():
    for service in DEMO_SERVICES:
        proc = rules.get_procedure(service)
        assert proc is not None
        for field in ("id", "name", "office", "requirements", "depends_on", "steps", "source_url"):
            assert field in proc, f"{service} missing {field}"
        assert proc["source_url"].startswith("http")
        assert proc["steps"], f"{service} has no steps"
        for step in proc["steps"]:
            assert step["title"] and step["source_url"].startswith("http")


def test_passport_requires_nic():
    reqs = rules.requirements("passport_application")
    assert "valid_nic" in reqs


def test_passport_depends_on_duplicate_nic():
    assert "duplicate_nic" in rules.depends_on("passport_application")


def test_dependency_condition_locks_on_missing_nic():
    conds = rules.dependency_conditions("passport_application")
    assert any(c["when_missing"] == "valid_nic" and c["service"] == "duplicate_nic" for c in conds)


def test_unknown_service_is_safe():
    assert rules.get_procedure("nope") is None
    assert rules.requirements("nope") == []
    assert rules.steps("nope") == []
    assert rules.name("nope") == "nope"  # falls back to the id
