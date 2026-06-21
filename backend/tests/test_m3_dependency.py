"""Owner: M3. Dependency node — the DoD: lost NIC locks the passport step. No DB."""
from app.graph.nodes.dependency import dependency


def test_lost_nic_locks_passport():
    """The headline demo: 'lost NIC -> passport' must lock passport behind NIC."""
    state = {
        "detected_services": ["passport_application"],
        "intent": {"missing_requirements": ["valid_nic"]},
    }
    out = dependency(state)
    graph = out["dependency_graph"]

    passport = graph["services"]["passport_application"]
    assert passport["status"] == "locked"
    assert "duplicate_nic" in passport["blocked_by"]
    assert passport["reason"]  # human-readable reason present

    # Prerequisite service is pulled into the plan and ordered first.
    assert "duplicate_nic" in graph["services"]
    assert graph["order"].index("duplicate_nic") < graph["order"].index("passport_application")
    assert "passport_application" in graph["locked"]


def test_valid_nic_does_not_lock_passport():
    state = {
        "detected_services": ["passport_application"],
        "intent": {"satisfied_requirements": ["valid_nic"]},
    }
    out = dependency(state)
    passport = out["dependency_graph"]["services"]["passport_application"]
    assert passport["status"] == "ready"
    assert out["dependency_graph"]["locked"] == []


def test_accepted_document_satisfies_requirement():
    state = {
        "detected_services": ["passport_application"],
        "documents": [{"type": "valid_nic", "status": "accepted"}],
    }
    out = dependency(state)
    assert out["dependency_graph"]["services"]["passport_application"]["status"] == "ready"


def test_license_renewal_also_locks_on_missing_nic():
    state = {
        "detected_services": ["driving_license_renewal"],
        "intent": {"missing_requirements": ["valid_nic"]},
    }
    out = dependency(state)
    node = out["dependency_graph"]["services"]["driving_license_renewal"]
    assert node["status"] == "locked"
    assert "duplicate_nic" in node["blocked_by"]


def test_node_writes_audit_log():
    state = {"detected_services": ["passport_application"], "intent": {"missing_requirements": ["valid_nic"]}}
    out = dependency(state)
    assert out["logs"], "dependency node should append an audit log entry"
    assert out["logs"][-1]["agent"] == "Dependency"
    assert out["logs"][-1]["confidence"] == 1.0  # deterministic
