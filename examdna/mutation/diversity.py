"""Duplicate detection and diversity selection.

Duplicates
    * ``surface``    — word-sequence similarity (difflib ratio) ≥ 0.8 between full texts
    * ``structural`` — identical structural signature: concept set, reasoning
      step-type sequence, input representations, answer type and given values

Diversity selection
    Greedy farthest-point selection. The distance used *for ordering only* is
    the mean of the structural dimension distances plus half the surface
    distance; it is a selection heuristic, not a reported quality metric.
    Ties are broken by item id, so the result is deterministic.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence, Tuple

from ..genome.compare import compare_genomes
from ..genome.graph import analyze_reasoning_graph
from ..utilities.stats import surface_similarity
from .properties import full_text

SURFACE_DUPLICATE = 0.8


def structural_signature(question: Dict[str, Any], genome: Dict[str, Any]) -> str:
    k = genome.get("knowledge") or {}
    concepts = sorted({(c or "").lower() for c in [k.get("primary_concept"), *(k.get("secondary_concepts") or [])] if c})
    payload = {
        "concepts": concepts,
        "steps": analyze_reasoning_graph(genome.get("reasoning") or {})["type_sequence"],
        "representation": sorted((genome.get("representation") or {}).get("input") or []),
        "answer": (genome.get("assessment") or {}).get("answer_type"),
        "given": sorted((g["symbol"], g.get("value")) for g in question.get("given") or []),
    }
    return json.dumps(payload, sort_keys=True)


def find_duplicates(items: Sequence[Tuple[Dict[str, Any], Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """``items`` is a sequence of (question, genome). Returns duplicate pairs."""
    out = []
    texts = [full_text(q) for q, _ in items]
    sigs = [structural_signature(q, g) for q, g in items]
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            reasons = []
            sim = surface_similarity(texts[i], texts[j])
            if sim >= SURFACE_DUPLICATE:
                reasons.append(f"surface similarity {sim:.2f}")
            if sigs[i] == sigs[j]:
                reasons.append("identical structural signature")
            if reasons:
                out.append({"a": items[i][0]["id"], "b": items[j][0]["id"], "reasons": reasons})
    return out


def _pair_distance(a, b) -> float:
    cmp = compare_genomes(a[1], b[1], full_text(a[0]), full_text(b[0]))
    s = cmp["similarity"]
    structural = sum(1 - s[d] for d in ("concept", "reasoning", "representation", "constraint", "answer")) / 5
    return structural + 0.5 * (1 - s["surface"])


def select_diverse(items: Sequence[Tuple[Dict[str, Any], Dict[str, Any]]], k: int) -> List[str]:
    if k <= 0 or not items:
        return []
    ordered = sorted(items, key=lambda it: it[0]["id"])
    chosen = [ordered[0]]
    remaining = ordered[1:]
    while remaining and len(chosen) < k:
        best = max(remaining, key=lambda it: (min(_pair_distance(it, c) for c in chosen), [-ord(ch) for ch in it[0]["id"]]))
        chosen.append(best)
        remaining.remove(best)
    return [q["id"] for q, _ in chosen]
