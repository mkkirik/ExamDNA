"""Explicit heuristic difficulty model.

This is a transparent rule, not a psychometric measure. It has not been
calibrated against student performance data. It exists so that "harder" and
"easier" can be expressed as concrete, inspectable feature changes.

    points = min(reasoning_stages, 6)
           + min(prerequisite_count, 4)
           + 2 * math_complexity            (0..3, so 0..6)
           + min(interacting_constraints, 4)
           + min(max(representation_count - 1, 0), 3)

    band = foundation  if points <= 6
           standard    if 7 <= points <= 12
           challenging if points >= 13
"""

from __future__ import annotations

from typing import Any, Dict, Optional

FEATURES = ["reasoning_stages", "prerequisite_count", "math_complexity", "interacting_constraints", "representation_count"]

DIFFICULTY_MODEL = {
    "name": "examdna-heuristic-v1",
    "status": "heuristic; not psychometrically validated",
    "formula": "min(stages,6) + min(prereqs,4) + 2*math_complexity + min(constraints,4) + min(max(representations-1,0),3)",
    "range": [0, 23],
    "bands": {"foundation": [0, 6], "standard": [7, 12], "challenging": [13, 23]},
    "features": FEATURES,
}


def difficulty_points(features: Dict[str, Any]) -> Optional[int]:
    if not features:
        return None
    try:
        stages = int(features.get("reasoning_stages", 0))
        prereq = int(features.get("prerequisite_count", 0))
        math_c = int(features.get("math_complexity", 0))
        cons = int(features.get("interacting_constraints", 0))
        reps = int(features.get("representation_count", 1))
    except (TypeError, ValueError):
        return None
    math_c = max(0, min(math_c, 3))
    return min(stages, 6) + min(prereq, 4) + 2 * math_c + min(cons, 4) + min(max(reps - 1, 0), 3)


def band_for(points: Optional[int]) -> Optional[str]:
    if points is None:
        return None
    if points <= 6:
        return "foundation"
    if points <= 12:
        return "standard"
    return "challenging"


def features_from_genome(genome: Dict[str, Any]) -> Dict[str, int]:
    """Derive difficulty features from a genome (deterministic counts).

    ``math_complexity`` cannot be counted and is taken from the genome's
    ``assessment.difficulty_features`` when the agent supplied it (default 1).
    """
    supplied = (genome.get("assessment") or {}).get("difficulty_features") or {}
    steps = (genome.get("reasoning") or {}).get("steps") or []
    knowledge = genome.get("knowledge") or {}
    constraints = genome.get("constraints") or {}
    reps = (genome.get("representation") or {}).get("input") or []
    n_constraints = len(constraints.get("explicit") or []) + len(constraints.get("boundary") or [])
    return {
        "reasoning_stages": len([s for s in steps if s.get("type") != "read_given"]),
        "prerequisite_count": len(knowledge.get("prerequisites") or []),
        "math_complexity": int(supplied.get("math_complexity", 1)),
        "interacting_constraints": n_constraints,
        "representation_count": max(len(reps), 1),
    }


def difficulty_estimate(features: Optional[Dict[str, Any]], source: str) -> Dict[str, Any]:
    points = difficulty_points(features or {})
    return {
        "model": DIFFICULTY_MODEL["name"],
        "points": points,
        "band": band_for(points),
        "features": features or None,
        "feature_source": source if points is not None else "unavailable",
        "status": "heuristic",
    }
