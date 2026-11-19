"""Transparent genome comparison.

Each dimension is reported separately as a similarity in [0, 1] together with
the method that produced it. Values are rounded to two decimals because the
underlying measures (set overlap, sequence edit distance) do not justify more
precision. No dimension is a semantic judgement; see docs/methodology.md.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..utilities.stats import jaccard, normalized_edit_similarity, surface_similarity, tokens
from .graph import analyze_reasoning_graph

METHODS = {
    "concept": "Jaccard overlap of {primary_concept} ∪ secondary_concepts (case-insensitive)",
    "learning_objectives": "Jaccard overlap of learning objective strings",
    "reasoning": "1 − normalized edit distance between step-type sequences in topological order, "
    "multiplied by 0.5 if the graph shape (linear vs branched) differs",
    "representation": "Jaccard overlap of input representation sets",
    "constraint": "Jaccard overlap of content words in explicit+domain+boundary constraints",
    "answer": "0.5 if answer types are equal + 0.5 if the answer units have the same physical dimension (or both are absent)",
    "surface": "difflib SequenceMatcher ratio over lower-cased word tokens of the full question text",
}


def _answer_similarity(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    aa, ab = a.get("assessment") or {}, b.get("assessment") or {}
    score = 0.5 if aa.get("answer_type") == ab.get("answer_type") else 0.0
    ua, ub = aa.get("answer_unit"), ab.get("answer_unit")
    if not ua and not ub:
        return score + 0.5
    if not ua or not ub:
        return score + 0.25  # one side unknown: cannot tell; count as half-matching
    try:
        from ..validation.units import parse_unit

        same = parse_unit(ua)[1] == parse_unit(ub)[1]
    except ValueError:
        same = ua.strip() == ub.strip()
    return score + (0.5 if same else 0.0)


def _concepts(g: Dict[str, Any]) -> set:
    k = g.get("knowledge") or {}
    return {c.strip().lower() for c in [k.get("primary_concept"), *(k.get("secondary_concepts") or [])] if c}


_STOP = {"the", "a", "an", "of", "is", "are", "to", "and", "be", "in", "on", "for", "must", "with", "that", "it", "as", "at", "by"}


def _constraint_words(g: Dict[str, Any]) -> set:
    c = g.get("constraints") or {}
    words = set()
    for key in ("explicit", "domain", "boundary"):
        for text in c.get(key) or []:
            words.update(t for t in tokens(text) if t not in _STOP)
    return words


def reasoning_similarity(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    ga = analyze_reasoning_graph(a.get("reasoning") or {})
    gb = analyze_reasoning_graph(b.get("reasoning") or {})
    sim = normalized_edit_similarity(ga["type_sequence"], gb["type_sequence"])
    if ga["is_linear"] != gb["is_linear"]:
        sim *= 0.5
    return sim


def compare_genomes(
    a: Dict[str, Any],
    b: Dict[str, Any],
    text_a: Optional[str] = None,
    text_b: Optional[str] = None,
) -> Dict[str, Any]:
    dims = {
        "concept": jaccard(_concepts(a), _concepts(b)),
        "learning_objectives": jaccard(
            {x.lower() for x in (a.get("knowledge") or {}).get("learning_objectives") or []},
            {x.lower() for x in (b.get("knowledge") or {}).get("learning_objectives") or []},
        ),
        "reasoning": reasoning_similarity(a, b),
        "representation": jaccard((a.get("representation") or {}).get("input") or [], (b.get("representation") or {}).get("input") or []),
        "constraint": jaccard(_constraint_words(a), _constraint_words(b)),
        "answer": _answer_similarity(a, b),
    }
    if text_a is not None and text_b is not None:
        dims["surface"] = surface_similarity(text_a, text_b)
    return {
        "a": a.get("genome_id"),
        "b": b.get("genome_id"),
        "similarity": {k: round(v, 2) for k, v in dims.items()},
        "methods": {k: METHODS[k] for k in dims},
        "note": "Structural similarity is not evidence of psychometric equivalence.",
    }
