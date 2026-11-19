"""Reasoning-graph analysis.

Reasoning is a directed acyclic graph of typed steps. Linear chains are a
special case; branches (one step feeding two) and joins (two feeding one) are
allowed. Topological order uses Kahn's algorithm with lexical tie-breaking so
it is deterministic.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List


def analyze_reasoning_graph(reasoning: Dict[str, Any]) -> Dict[str, Any]:
    steps = reasoning.get("steps") or []
    edges = reasoning.get("edges") or []
    errors: List[str] = []
    warnings: List[str] = []

    ids = [s.get("id") for s in steps]
    id_set = set(ids)
    if len(ids) != len(id_set):
        errors.append("duplicate reasoning step ids")
    type_of = {s.get("id"): s.get("type") for s in steps}

    out_edges: Dict[str, List[str]] = defaultdict(list)
    indeg = {i: 0 for i in id_set}
    for edge in edges:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            errors.append(f"malformed edge {edge!r}")
            continue
        a, b = edge
        if a not in id_set or b not in id_set:
            errors.append(f"edge {a}->{b} references an unknown step")
            continue
        if a == b:
            errors.append(f"self-loop on step {a}")
            continue
        out_edges[a].append(b)
        indeg[b] += 1

    # Kahn's algorithm
    ready = sorted(i for i, d in indeg.items() if d == 0)
    order: List[str] = []
    indeg_work = dict(indeg)
    while ready:
        node = ready.pop(0)
        order.append(node)
        for nxt in sorted(out_edges[node]):
            indeg_work[nxt] -= 1
            if indeg_work[nxt] == 0:
                ready.append(nxt)
                ready.sort()
    if len(order) != len(id_set) and not errors:
        errors.append("reasoning graph contains a cycle")

    connected = set()
    for a, targets in out_edges.items():
        connected.add(a)
        connected.update(targets)
    isolated = sorted(id_set - connected) if len(id_set) > 1 else []
    if isolated:
        warnings.append(f"steps not connected to any other step: {', '.join(isolated)}")

    branch_points = sorted(a for a, t in out_edges.items() if len(set(t)) > 1)
    join_points = sorted(b for b, d in indeg.items() if d > 1)
    sources = sorted(i for i, d in indeg.items() if d == 0)
    sinks = sorted(i for i in id_set if not out_edges.get(i))
    is_linear = not branch_points and not join_points and len(sources) <= 1 and not errors

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "topological_order": order if not errors else [],
        "type_sequence": [type_of[i] for i in order] if not errors else [type_of[i] for i in ids],
        "is_linear": is_linear,
        "branch_points": branch_points,
        "join_points": join_points,
        "sources": sources,
        "sinks": sinks,
        "step_count": len(ids),
        "edge_count": len(edges),
    }


def linear_reasoning(step_types: List[str], descriptions: List[str] | None = None) -> Dict[str, Any]:
    """Convenience constructor for a simple chain of steps."""
    steps = []
    for i, t in enumerate(step_types, 1):
        step = {"id": f"s{i}", "type": t}
        if descriptions and i - 1 < len(descriptions):
            step["description"] = descriptions[i - 1]
        steps.append(step)
    edges = [[f"s{i}", f"s{i + 1}"] for i in range(1, len(step_types))]
    return {"steps": steps, "edges": edges}
