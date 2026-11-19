"""Shared test fixtures (synthetic data only)."""

from __future__ import annotations

import copy
import functools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUTS = ROOT / "examples" / "synthetic_inputs"
for p in (str(ROOT), str(ROOT / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

from examdna.extraction.normalize import normalize_bank  # noqa: E402
from examdna.genome import build_genomes  # noqa: E402
from examdna.utilities.io import read_json_file  # noqa: E402

DEMO_QUESTIONS = "p1-a2,p1-a3,p1-a4,p1-a6,p2-a2,p2-a3,p2-a4,p2-a5,p3-a2,p3-a3,p3-a4,p1-b1,p1-b2,p1-b3,p2-b1,p2-b3,p3-b1,p3-b2".split(",")


@functools.lru_cache(maxsize=None)
def _bank():
    return normalize_bank(read_json_file(INPUTS / "physics_bank.json"))


def bank():
    return copy.deepcopy(_bank())


@functools.lru_cache(maxsize=None)
def _genomes():
    return build_genomes(_bank(), read_json_file(INPUTS / "annotations.json"))["genomes"]


def genomes():
    return copy.deepcopy(_genomes())


def mini_question(**overrides):
    q = {
        "id": "q1",
        "text": "A cart of mass 2.0 kg accelerates at 3.0 m/s^2. Calculate the resultant force.",
        "question_type": "calculation",
        "marks": 2,
        "section": "A",
        "topic": "Forces",
        "learning_objectives": ["F1"],
        "cognitive_level": "application",
        "given": [{"symbol": "m", "value": 2.0, "unit": "kg"}, {"symbol": "a", "value": 3.0, "unit": "m/s^2"}],
        "marking": {"final_answer": "6.0 N", "points": [{"description": "F = ma", "marks": 1}, {"description": "6.0 N", "marks": 1}]},
        "source": {"document": "Mini paper"},
    }
    q.update(overrides)
    return q


def demo_candidates(plan):
    import build_demo_candidates

    index = {(s["parent_id"], s["operator"]): s["spec_id"] for s in plan["specs"]}
    return build_demo_candidates.build(lambda parent, op: index[(parent, op)])
