"""Genome construction.

``build_genome`` merges three sources, recording provenance per field:

1. the normalized question (``explicit``/source fields),
2. deterministic derivations by this software (``calculated``: command term,
   answer type from question type, max marks, marking components),
3. an optional annotation written by the agent (``inferred``: concepts,
   reasoning graph, constraints, representations).

Fields with no source are left empty and listed under
``validation.missing_components``; they are never fabricated.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Optional, Tuple

from .. import SCHEMA_VERSION
from ..fingerprint.difficulty import difficulty_estimate, features_from_genome
from ..models.constants import COMMAND_TERMS, NOT_VERIFIED, QUESTION_TYPE_TO_ANSWER_TYPE
from ..models.schema import validate
from ..utilities.io import InputError
from .graph import analyze_reasoning_graph


def detect_command_term(text: str) -> Optional[str]:
    lowered = (text or "").lower()
    best: Tuple[int, Optional[str]] = (len(lowered) + 1, None)
    for term in COMMAND_TERMS:
        m = re.search(r"\b" + re.escape(term) + r"\b", lowered)
        if m and m.start() < best[0]:
            best = (m.start(), term)
    return best[1]


def _full_text(question: Dict[str, Any]) -> str:
    parts = " ".join(p["text"] for p in question.get("parts") or [])
    return f"{question['text']} {parts}".strip()


def build_genome(question: Dict[str, Any], annotation: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ann = copy.deepcopy(annotation or {})
    prov: Dict[str, str] = {}

    def take(section: str, key: str, fallback: Any, fallback_prov: Optional[str]) -> Any:
        sec = ann.get(section) or {}
        if key in sec and sec[key] not in (None, [], ""):
            prov[f"{section}.{key}"] = (ann.get("field_provenance") or {}).get(f"{section}.{key}", "inferred")
            return sec[key]
        if fallback not in (None, [], ""):
            if fallback_prov:
                prov[f"{section}.{key}"] = fallback_prov
            return fallback
        return copy.deepcopy(fallback)

    q_prov = question.get("provenance", {})
    knowledge = {
        "primary_concept": take("knowledge", "primary_concept", None, None),
        "secondary_concepts": take("knowledge", "secondary_concepts", [], None),
        "prerequisites": take("knowledge", "prerequisites", [], None),
        "learning_objectives": take(
            "knowledge", "learning_objectives", list(question.get("learning_objectives") or []), q_prov.get("learning_objectives", "unverified")
        ),
        "topic": question.get("topic"),
        "subtopic": question.get("subtopic"),
    }

    reasoning_in = ann.get("reasoning") or {}
    reasoning = {
        "steps": reasoning_in.get("steps") or [],
        "edges": reasoning_in.get("edges") or [],
        "expected_inference": reasoning_in.get("expected_inference"),
        "justification_required": bool(reasoning_in.get("justification_required", False)),
    }
    if reasoning["steps"]:
        prov["reasoning"] = (ann.get("field_provenance") or {}).get("reasoning", "inferred")

    rep_in = ann.get("representation") or {}
    default_input = ["verbal"]
    if question.get("table"):
        default_input.append("table")
    if question.get("diagram_description"):
        default_input.append("diagram")
    representation = {
        "input": rep_in.get("input") or default_input,
        "output": rep_in.get("output") or [],
        "context": rep_in.get("context"),
    }
    prov["representation.input"] = "inferred" if rep_in.get("input") else "calculated"

    con_in = ann.get("constraints") or {}
    explicit_from_q = [c["text"] for c in question.get("constraints") or [] if c.get("kind") in (None, "explicit")]
    units_from_q = sorted({g["unit"] for g in question.get("given") or [] if g.get("unit")})
    constraints = {
        "explicit": con_in.get("explicit") or explicit_from_q,
        "implicit": con_in.get("implicit") or [],
        "domain": con_in.get("domain") or [c["text"] for c in question.get("constraints") or [] if c.get("kind") == "domain"],
        "boundary": con_in.get("boundary") or [c["text"] for c in question.get("constraints") or [] if c.get("kind") == "boundary"],
        "units": con_in.get("units") or units_from_q,
        "precision": con_in.get("precision"),
    }

    marking = question.get("marking") or {}
    qtype = question.get("question_type")
    command_term = (ann.get("assessment") or {}).get("command_term") or detect_command_term(_full_text(question))
    prov["assessment.command_term"] = "inferred" if (ann.get("assessment") or {}).get("command_term") else "calculated"
    answer_type = (ann.get("assessment") or {}).get("answer_type") or (QUESTION_TYPE_TO_ANSWER_TYPE.get(qtype) if qtype else None)
    if answer_type:
        prov["assessment.answer_type"] = "inferred" if (ann.get("assessment") or {}).get("answer_type") else "calculated"
    assessment = {
        "command_term": command_term,
        "question_type": qtype,
        "cognitive_level": question.get("cognitive_level") or (ann.get("assessment") or {}).get("cognitive_level"),
        "max_marks": question.get("marks"),
        "answer_type": answer_type,
        "expected_answer": marking.get("final_answer") or (ann.get("assessment") or {}).get("expected_answer"),
        "answer_unit": (ann.get("assessment") or {}).get("answer_unit")
        or (((question.get("extensions") or {}).get("verification") or {}).get("claimed_unit")),
        "marking_components": [{"description": p["description"], "marks": p["marks"]} for p in marking.get("points") or []],
        "difficulty_features": (ann.get("assessment") or {}).get("difficulty_features") or question.get("difficulty_features") or {},
    }

    genome = {
        "schema_version": SCHEMA_VERSION,
        "genome_id": f"g-{question['id']}"[:128],
        "question_id": question["id"],
        "parent_question_id": (question.get("lineage") or {}).get("parent_id"),
        "provenance": {
            "origin": question["source"]["origin"],
            "document": question["source"].get("document"),
            "page": question["source"].get("page"),
        },
        "lineage": ann.get("lineage") or [],
        "knowledge": knowledge,
        "reasoning": reasoning,
        "representation": representation,
        "constraints": constraints,
        "assessment": assessment,
        "validation": {},
        "field_provenance": prov,
    }
    return finalize_genome(genome)


def finalize_genome(genome: Dict[str, Any]) -> Dict[str, Any]:
    """(Re)compute deterministic validation fields and difficulty for a genome."""
    missing: List[str] = []
    if not genome["knowledge"].get("primary_concept"):
        missing.append("knowledge.primary_concept")
    if not genome["knowledge"].get("learning_objectives"):
        missing.append("knowledge.learning_objectives")
    if not genome["reasoning"].get("steps"):
        missing.append("reasoning.steps")
    if genome["assessment"].get("max_marks") is None:
        missing.append("assessment.max_marks")
    if not genome["assessment"].get("answer_type"):
        missing.append("assessment.answer_type")
    if not genome["assessment"].get("marking_components"):
        missing.append("assessment.marking_components")

    graph = analyze_reasoning_graph(genome["reasoning"])
    critical = {"knowledge.primary_concept", "reasoning.steps"}
    if not missing:
        completeness = "complete"
    elif critical & set(missing):
        completeness = "minimal"
    else:
        completeness = "partial"

    prior = genome.get("validation") or {}
    genome["assessment"]["difficulty"] = difficulty_estimate(features_from_genome(genome), "genome") if genome["reasoning"]["steps"] else difficulty_estimate(None, "unavailable")
    genome["validation"] = {
        "structural_completeness": completeness,
        "missing_components": missing,
        "solvability": prior.get("solvability", NOT_VERIFIED),
        "answer_validation": prior.get("answer_validation", NOT_VERIFIED),
        "uniqueness": prior.get("uniqueness", "unknown"),
        "human_review_required": bool(missing) or not graph["valid"] or prior.get("human_review_required", False),
        "confidence": "high" if completeness == "complete" and graph["valid"] else ("medium" if completeness == "partial" else "low"),
        "graph_errors": graph["errors"],
    }
    return genome


def check_genome(genome: Dict[str, Any]) -> List[str]:
    """Schema errors plus reasoning-graph errors."""
    errors = validate(genome, "genome")
    if not errors:
        errors.extend(f"reasoning: {e}" for e in analyze_reasoning_graph(genome["reasoning"])["errors"])
    return errors


def build_genomes(bank: Dict[str, Any], annotations: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build genomes for every question in a bank.

    ``annotations`` is ``{"annotations": {question_id: {...}}}`` or a plain
    mapping. Annotations for unknown question IDs are rejected.
    """
    ann_map = (annotations or {}).get("annotations", annotations or {})
    if not isinstance(ann_map, dict):
        raise InputError("annotations must be an object keyed by question id")
    known = {q["id"] for q in bank["questions"]}
    unknown = sorted(set(ann_map) - known)
    if unknown:
        raise InputError(f"annotations reference unknown question ids: {', '.join(unknown[:10])}")
    genomes, problems = [], {}
    for q in bank["questions"]:
        g = build_genome(q, ann_map.get(q["id"]))
        errs = check_genome(g)
        if errs:
            problems[q["id"]] = errs
        genomes.append(g)
    return {
        "schema_version": SCHEMA_VERSION,
        "bank_id": bank.get("bank_id"),
        "genomes": genomes,
        "report": {
            "count": len(genomes),
            "complete": sum(1 for g in genomes if g["validation"]["structural_completeness"] == "complete"),
            "partial": sum(1 for g in genomes if g["validation"]["structural_completeness"] == "partial"),
            "minimal": sum(1 for g in genomes if g["validation"]["structural_completeness"] == "minimal"),
            "errors": problems,
        },
    }
