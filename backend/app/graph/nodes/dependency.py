"""Owner: M3. Dependency node — build the graph from JSON rules, lock blocked steps.

Pure rules -> reliable and auditable (no LLM in the decision path). From the
detected services it:

  * builds a per-service dependency graph from each service's ``depends_on`` and
    ``dependency_conditions`` in the rules layer,
  * decides which services are blocked because a required input is missing
    (e.g. a lost NIC blocks the passport application),
  * marks blocked services ``locked`` with a human-readable reason and records the
    prerequisite service that unlocks them,
  * produces a topologically ordered service list so prerequisites come first.

Writes ``dependency_graph`` into GraphState. Shape::

    {
      "services": {
        "<service_id>": {
          "name": str,
          "depends_on": [service_id, ...],
          "status": "ready" | "locked",
          "reason": str | None,
          "blocked_by": [service_id, ...],
        }, ...
      },
      "order": [service_id, ...],     # prerequisites first
      "locked": [service_id, ...],
    }
"""
from __future__ import annotations

from typing import Any

from app.graph.nodes.audit import audit
from app.graph.state import GraphState
from app.rag import rules
from app.schemas.document import SATISFIED_STATUSES


def _satisfied_requirements(state: GraphState) -> set[str]:
    """Requirement keys the citizen already has.

    Sources, in order of trust:
      * ``intent.satisfied_requirements`` / ``intent.have`` — planner-extracted.
      * accepted ``documents`` — their ``type`` counts as satisfied.
    A requirement is otherwise assumed *not* satisfied (conservative: we'd rather
    surface a prerequisite than skip one).
    """
    have: set[str] = set()
    intent = state.get("intent") or {}
    for key in ("satisfied_requirements", "have"):
        val = intent.get(key) if isinstance(intent, dict) else None
        if isinstance(val, list):
            have.update(str(v) for v in val)
    for doc in state.get("documents") or []:
        # "confirmed" counts as well as "accepted": a citizen who told us they
        # hold a valid NIC must not get a duplicate-NIC prerequisite bolted on.
        if (
            isinstance(doc, dict)
            and doc.get("status") in SATISFIED_STATUSES
            and doc.get("type")
        ):
            have.add(str(doc["type"]))
    return have


def _missing_requirements(state: GraphState) -> set[str]:
    """Requirement keys the citizen EXPLICITLY doesn't have (hard blockers).

    Only ``lost`` qualifies — the LLM planner speculatively fills ``missing``
    with things a procedure will probably need, and locking real steps behind
    guesses dead-ends cases. Unconfirmed requirements are the eligibility
    node's job (clarifying questions), not lock reasons.
    """
    missing: set[str] = set()
    intent = state.get("intent") or {}
    if isinstance(intent, dict):
        for key in ("missing_requirements", "lost"):
            val = intent.get(key)
            if isinstance(val, list):
                missing.update(str(v) for v in val)
    return missing


# A missing requirement that a known rules-based procedure can produce. Lets a
# custom goal pull in real prerequisite workflows (e.g. lost NIC → duplicate NIC
# steps come first) exactly like the rules path does. Now lives in the rules
# layer because "How to get it?" needs the same mapping to word its sub-goal.
_REQ_FULFILLED_BY = rules.REQUIREMENT_SERVICE


def _custom_dependency(custom_steps: list[dict], missing: set[str]) -> dict[str, Any]:
    """Deterministic dependency graph for an LLM-generated custom procedure.

    Never LLM-locked (locking a custom procedure with no unlockable prerequisite
    would dead-end the case). Instead, when an explicitly-missing requirement is
    producible by a known service, that service is prepended as a real,
    actionable prerequisite and the custom procedure is locked behind it.
    """
    name = (
        custom_steps[0].get("_service_name", "Custom Procedure")
        if custom_steps else "Custom Procedure"
    )
    prereqs = [
        svc for req, svc in _REQ_FULFILLED_BY.items()
        if req in missing and rules.steps(svc)
    ]

    services: dict[str, Any] = {}
    for svc in prereqs:
        services[svc] = {
            "name": rules.name(svc),
            "depends_on": [],
            "status": "ready",
            "reason": None,
            "blocked_by": [],
        }
    services["custom_procedure"] = {
        "name": name,
        "depends_on": list(prereqs),
        "status": "locked" if prereqs else "ready",
        "reason": (
            f"Complete first: {', '.join(rules.name(s) for s in prereqs)}."
            if prereqs else None
        ),
        "blocked_by": list(prereqs),
    }
    return {
        "services": services,
        "order": [*prereqs, "custom_procedure"],
        "locked": ["custom_procedure"] if prereqs else [],
    }


def dependency(state: GraphState) -> dict:
    services = list(state.get("detected_services") or [])
    satisfied = _satisfied_requirements(state)
    explicit_missing = _missing_requirements(state)

    # Custom goals: deterministic graph; known services can be pulled in as
    # prerequisites for explicitly missing requirements.
    if services == ["custom_procedure"]:
        dependency_graph = _custom_dependency(
            state.get("custom_steps") or [],
            explicit_missing,
        )
        svc_node = dependency_graph["services"].get("custom_procedure", {})
        locked = dependency_graph.get("locked", [])
        log = audit(
            state,
            agent="Dependency",
            decision=f"custom_procedure: {'locked' if locked else 'ready'}" + (f" — {svc_node.get('reason')}" if locked else ""),
            reason=svc_node.get("reason"),
            confidence=1.0,
        )
        return {"dependency_graph": dependency_graph, **log}

    graph: dict[str, dict[str, Any]] = {}
    extra_prereqs: list[str] = []

    def ensure_node(service: str) -> dict[str, Any]:
        if service not in graph:
            graph[service] = {
                "name": rules.name(service),
                "depends_on": [],
                "status": "ready",
                "reason": None,
                "blocked_by": [],
            }
        return graph[service]

    for service in services:
        node = ensure_node(service)
        node["depends_on"] = list(rules.depends_on(service))

        # Conditional dependencies: an explicitly missing requirement pulls in a
        # prerequisite service and locks this one until that prerequisite is
        # done. Unconfirmed requirements do NOT lock (e.g. a licence renewal is
        # not chained behind a duplicate-NIC procedure just because the citizen
        # never mentioned their NIC) — an accepted document also clears it.
        for cond in rules.dependency_conditions(service):
            req = cond.get("when_missing")
            prereq = cond.get("service")
            req_missing = bool(req) and req in explicit_missing and req not in satisfied
            if req_missing and prereq:
                node["status"] = "locked"
                node["reason"] = cond.get("reason") or f"{rules.name(prereq)} required first."
                if prereq not in node["blocked_by"]:
                    node["blocked_by"].append(prereq)
                if prereq not in services and prereq not in extra_prereqs:
                    extra_prereqs.append(prereq)

    # Materialise any prerequisite services that weren't detected on their own.
    for prereq in extra_prereqs:
        ensure_node(prereq)

    order = _topo_order(graph)
    locked = [s for s, n in graph.items() if n["status"] == "locked"]

    dependency_graph = {"services": graph, "order": order, "locked": locked}

    if locked:
        first = locked[0]
        decision = "; ".join(f"{graph[s]['name']} locked" for s in locked)
        reason = graph[first]["reason"]
    else:
        decision = "No blocking dependencies; all detected services are ready."
        reason = None

    log = audit(
        state,
        agent="Dependency",
        decision=decision,
        reason=reason,
        source_url=rules.source_url(locked[0]) if locked else None,
        confidence=1.0,  # deterministic
    )

    return {"dependency_graph": dependency_graph, **log}


def _topo_order(graph: dict[str, dict[str, Any]]) -> list[str]:
    """Topological order over the subgraph induced by ``graph`` (prereqs first).

    Edges only count when the dependency is itself a node in ``graph`` (so an
    unrelated ``depends_on`` entry doesn't pull in noise). Cycles fall back to a
    stable insertion order rather than raising.
    """
    nodes = list(graph.keys())
    deps = {
        s: [d for d in (graph[s]["depends_on"] + graph[s]["blocked_by"]) if d in graph]
        for s in nodes
    }
    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(s: str) -> None:
        if s in visited or s in visiting:
            return
        visiting.add(s)
        for d in deps[s]:
            visit(d)
        visiting.discard(s)
        visited.add(s)
        ordered.append(s)

    for s in nodes:
        visit(s)
    return ordered
