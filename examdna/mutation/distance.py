"""Mutation distance: how far a child moved from its parent, per dimension.

distance = 1 − similarity (see genome/compare.py for each similarity).
Labels: none (< 0.05), low (< 0.34), moderate (< 0.67), high (≥ 0.67).
The six dimensions are never collapsed into a single score.

Novelty classification
----------------------
* ``near_duplicate``   — surface distance < 0.2 (word-sequence similarity
  > 0.8) and no structural change
* ``parameter_novelty`` — wording and given values changed, structure unchanged
* ``surface_novelty``  — wording changed, structure and values unchanged
* ``structural_novelty`` — at least one of reasoning / representation /
  constraint / answer distance ≥ low
* conceptual equivalence is a semantic claim; it is only reported when the
  agent supplied a judgement, and is labelled ``model_assisted``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..genome.compare import compare_genomes
from .properties import full_text

LABELS = [(0.05, "none"), (0.34, "low"), (0.67, "moderate"), (1.01, "high")]
STRUCTURAL = ["reasoning", "representation", "constraint", "answer"]
# Primary-concept preservation is enforced separately by operator contracts;
# this cap bounds drift in the *set* of concepts (primary + secondary).
MODE_CONCEPT_LIMIT = {"conservative": "low", "balanced": "moderate", "exploratory": "high"}
_ORDER = ["none", "low", "moderate", "high"]


def label(distance: float) -> str:
    for limit, name in LABELS:
        if distance < limit:
            return name
    return "high"


def label_at_most(lbl: str, cap: str) -> bool:
    return _ORDER.index(lbl) <= _ORDER.index(cap)


def distance_profile(
    parent_q: Dict[str, Any],
    parent_g: Dict[str, Any],
    child_q: Dict[str, Any],
    child_g: Dict[str, Any],
    judgements: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    cmp = compare_genomes(parent_g, child_g, full_text(parent_q), full_text(child_q))
    sim = cmp["similarity"]
    dims = {}
    for name in ("surface", "concept", "reasoning", "representation", "constraint", "answer"):
        d = round(1.0 - sim[name], 2)
        dims[name] = {"distance": d, "label": label(d), "method": cmp["methods"][name]}
    structural_change = any(dims[d]["label"] != "none" for d in STRUCTURAL)
    givens_p = {g["symbol"]: g.get("value") for g in parent_q.get("given") or []}
    givens_c = {g["symbol"]: g.get("value") for g in child_q.get("given") or []}
    if structural_change:
        novelty = "structural_novelty"
    elif givens_p != givens_c and dims["surface"]["distance"] >= 0.2:
        novelty = "parameter_novelty"
    elif dims["surface"]["distance"] < 0.2:
        novelty = "near_duplicate"
    else:
        novelty = "surface_novelty"
    judgements = judgements or {}
    equivalence = None
    if "primary_concept" in judgements or "target_skill" in judgements:
        equivalence = {
            "status": "model_assisted",
            "conceptually_equivalent": bool(judgements.get("primary_concept", judgements.get("target_skill"))),
        }
    return {
        "dimensions": dims,
        "novelty": novelty,
        "conceptual_equivalence": equivalence or {"status": "unverified"},
        "note": "Distances are transparent set/sequence measures; they do not establish psychometric equivalence.",
    }


def within_mode(profile: Dict[str, Any], mode: str) -> Optional[str]:
    """Return a message if the concept distance exceeds the mode's limit."""
    cap = MODE_CONCEPT_LIMIT.get(mode, "low")
    lbl = profile["dimensions"]["concept"]["label"]
    if not label_at_most(lbl, cap):
        return f"concept distance '{lbl}' exceeds the '{cap}' limit for {mode} mode"
    return None
