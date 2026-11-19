"""Mutation lineage: question families across generations."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence


def build_lineage(questions: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a lineage forest from questions (source + generated).

    Generated questions carry ``lineage.parent_id``. Checks: parent exists,
    no cycles, generation == parent generation + 1, root_id consistent.
    """
    by_id = {q["id"]: q for q in questions}
    nodes: Dict[str, Dict[str, Any]] = {}
    errors: List[str] = []
    for q in questions:
        lin = q.get("lineage") or {}
        nodes[q["id"]] = {
            "id": q["id"],
            "parent": lin.get("parent_id"),
            "operator": lin.get("operator"),
            "generation": lin.get("generation", 0) if lin else 0,
            "state": (q.get("validation") or {}).get("state", "SOURCE" if not lin else "NOT_VERIFIED"),
            "children": [],
        }
    for nid, node in nodes.items():
        parent = node["parent"]
        if parent is None:
            continue
        if parent not in nodes:
            errors.append(f"{nid}: parent {parent} not found")
            continue
        nodes[parent]["children"].append(nid)
        expected = (nodes[parent]["generation"] or 0) + 1
        if node["generation"] != expected:
            errors.append(f"{nid}: generation {node['generation']} but parent {parent} is generation {nodes[parent]['generation']}")
    # cycle detection + root resolution
    roots: Dict[str, str] = {}
    for nid in nodes:
        seen, cur = [], nid
        while cur is not None and cur in nodes:
            if cur in seen:
                errors.append(f"lineage cycle involving {nid}")
                break
            seen.append(cur)
            cur = nodes[cur]["parent"]
        roots[nid] = seen[-1]
        declared = (by_id[nid].get("lineage") or {}).get("root_id")
        if declared and declared != roots[nid] and not any("cycle" in e and nid in e for e in errors):
            errors.append(f"{nid}: declared root {declared} but lineage resolves to {roots[nid]}")
    for node in nodes.values():
        node["children"].sort()
        node["root"] = roots[node["id"]]
    families: Dict[str, List[str]] = {}
    for nid, root in roots.items():
        families.setdefault(root, []).append(nid)
    return {
        "nodes": dict(sorted(nodes.items())),
        "families": {k: sorted(v) for k, v in sorted(families.items())},
        "valid": not errors,
        "errors": sorted(set(errors)),
        "max_generation": max((n["generation"] or 0 for n in nodes.values()), default=0),
    }


def render_tree(lineage: Dict[str, Any], only_families_with_children: bool = True) -> str:
    nodes = lineage["nodes"]
    lines: List[str] = []

    def walk(nid: str, prefix: str, last: bool, top: bool):
        n = nodes[nid]
        label = nid if top else f"{n['operator']} → {nid} [{n['state']}]"
        lines.append(label if top else f"{prefix}{'└── ' if last else '├── '}{label}")
        child_prefix = "" if top else prefix + ("    " if last else "│   ")
        kids = n["children"]
        for i, c in enumerate(kids):
            walk(c, child_prefix, i == len(kids) - 1, False)

    for root in lineage["families"]:
        if nodes[root]["parent"] is not None and root in nodes and nodes[root]["parent"] in nodes:
            continue
        if only_families_with_children and not nodes[root]["children"]:
            continue
        walk(root, "", True, True)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
