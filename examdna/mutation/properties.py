"""Deterministic property checks between a parent and a child question.

Each checker returns ``True`` (property unchanged), ``False`` (changed) or
``None`` (cannot be decided deterministically — a model-assisted judgement
is required).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from ..fingerprint.difficulty import difficulty_points, features_from_genome
from ..genome.graph import analyze_reasoning_graph
from ..utilities.stats import surface_similarity, tokens

WORDING_SIMILARITY_LIMIT = 0.8


def full_text(q: Dict[str, Any]) -> str:
    parts = " ".join(p["text"] for p in q.get("parts") or [])
    opts = " ".join(o["text"] for o in q.get("options") or [])
    return " ".join(x for x in (q.get("text", ""), parts, opts) if x).strip()


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _given_values(q):
    return {g["symbol"]: g.get("value") for g in q.get("given") or [] if g.get("role") != "constant"}


def _constraint_words(g):
    c = g.get("constraints") or {}
    words = set()
    for key in ("explicit", "domain", "boundary"):
        for t in c.get(key) or []:
            words.update(tokens(t))
    return words


def _concepts(g):
    k = g.get("knowledge") or {}
    return {_norm(c) for c in [k.get("primary_concept"), *(k.get("secondary_concepts") or [])] if c}


def _seq(g):
    return analyze_reasoning_graph(g.get("reasoning") or {})["type_sequence"]


Checker = Callable[[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]], Optional[bool]]

UNCHANGED: Dict[str, Checker] = {
    "primary_concept": lambda pq, pg, cq, cg: _norm(pg["knowledge"].get("primary_concept")) == _norm(cg["knowledge"].get("primary_concept")),
    "learning_objectives": lambda pq, pg, cq, cg: {_norm(x) for x in pg["knowledge"].get("learning_objectives") or []}
    <= {_norm(x) for x in cg["knowledge"].get("learning_objectives") or []},
    "topic": lambda pq, pg, cq, cg: _norm(pq.get("topic")) == _norm(cq.get("topic")),
    "question_type": lambda pq, pg, cq, cg: pq.get("question_type") == cq.get("question_type"),
    "answer_type": lambda pq, pg, cq, cg: pg["assessment"].get("answer_type") == cg["assessment"].get("answer_type"),
    "marks": lambda pq, pg, cq, cg: pq.get("marks") == cq.get("marks"),
    "reasoning_structure": lambda pq, pg, cq, cg: _seq(pg) == _seq(cg),
    "representation": lambda pq, pg, cq, cg: set(pg["representation"].get("input") or []) == set(cg["representation"].get("input") or []),
    "numeric_parameters": lambda pq, pg, cq, cg: _given_values(pq) == _given_values(cq),
    "constraints": lambda pq, pg, cq, cg: _constraint_words(pg) == _constraint_words(cg),
    "context": lambda pq, pg, cq, cg: (
        None
        if not (pg["representation"].get("context") and cg["representation"].get("context"))
        else _norm(pg["representation"].get("context")) == _norm(cg["representation"].get("context"))
    ),
    "wording": lambda pq, pg, cq, cg: surface_similarity(full_text(pq), full_text(cq)) >= WORDING_SIMILARITY_LIMIT,
    "reasoning_direction": lambda pq, pg, cq, cg: not (set(_given_values(pq)) - set(_given_values(cq))),
    "difficulty_features": lambda pq, pg, cq, cg: difficulty_points(features_from_genome(pg)) == difficulty_points(features_from_genome(cg)),
    "concept_set": lambda pq, pg, cq, cg: not (_concepts(cg) > _concepts(pg)),
}


def property_unchanged(name: str, pq, pg, cq, cg) -> Optional[bool]:
    checker = UNCHANGED.get(name)
    if checker is None:
        return None
    return checker(pq, pg, cq, cg)


def difficulty_delta(pg: Dict[str, Any], cg: Dict[str, Any]) -> Optional[int]:
    a = difficulty_points(features_from_genome(pg))
    b = difficulty_points(features_from_genome(cg))
    if a is None or b is None:
        return None
    return b - a
