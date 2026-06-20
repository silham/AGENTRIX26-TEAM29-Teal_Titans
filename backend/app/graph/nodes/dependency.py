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
        if isinstance(doc, dict) and doc.get("status") == "accepted" and doc.get("type"):
            have.add(str(doc["type"]))
    return have


def _missing_requirements(state: GraphState) -> set[str]:
    """Requirement keys explicitly flagged as missing/lost by the planner."""
    missing: set[str] = set()
    intent = state.get("intent") or {}
    if isinstance(intent, dict):
        for key in ("missing_requirements", "missing", "lost"):
            val = intent.get(key)
            if isinstance(val, list):
                missing.update(str(v) for v in val)
    return missing


def dependency(state: GraphState) -> dict:
    services = list(state.get("detected_services") or [])
    satisfied = _satisfied_requirements(state)
    explicit_missing = _missing_requirements(state)

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

        # Conditional dependencies: a missing requirement pulls in a prerequisite
        # service and locks this one until that prerequisite is done.
        for cond in rules.dependency_conditions(service):
            req = cond.get("when_missing")
            prereq = cond.get("service")
            req_missing = bool(req) and (req in explicit_missing or req not in satisfied)
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
