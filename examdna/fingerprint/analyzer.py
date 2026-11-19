"""Exam DNA analyzer.

Reconstructs observable structural characteristics of a set of source
papers. Every number in the output is computed from the input bank; each
distribution carries the question IDs that support it.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Any, Dict, List, Optional

from .. import SCHEMA_VERSION
from ..models.constants import COGNITIVE_LEVELS, DIFFICULTY_BANDS, QUESTION_TYPES, REASONING_STEP_TYPES, REPRESENTATIONS
from ..models.schema import validate
from ..utilities.ids import stable_id
from ..utilities.stats import evidence_level, frequency, median, proportions, summary
from .difficulty import DIFFICULTY_MODEL, difficulty_estimate, features_from_genome


def question_difficulty(question: Dict[str, Any], genome: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if genome is not None:
        return difficulty_estimate(features_from_genome(genome), "genome")
    if question.get("difficulty_features"):
        return difficulty_estimate(question["difficulty_features"], "question.difficulty_features")
    return difficulty_estimate(None, "unavailable")


def _weighted(questions: List[Dict[str, Any]], key) -> Dict[str, Any]:
    counts: Dict[str, int] = defaultdict(int)
    marks: Dict[str, int] = defaultdict(int)
    evidence: Dict[str, List[str]] = defaultdict(list)
    unknown = []
    for q in questions:
        values = key(q)
        if not values:
            unknown.append(q["id"])
            continue
        for v in values:
            counts[v] += 1
            marks[v] += q["marks"] or 0
            evidence[v].append(q["id"])
    return {
        "counts": dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "share_by_count": proportions(dict(counts)),
        "share_by_marks": proportions(dict(marks)) if sum(marks.values()) else {},
        "unclassified": unknown,
        "evidence": {k: v for k, v in sorted(evidence.items())},
    }


def analyze_bank(
    bank: Dict[str, Any],
    genomes: Optional[List[Dict[str, Any]]] = None,
    *,
    preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build an Exam DNA profile from a normalized bank (and optional genomes)."""
    genome_by_q = {g["question_id"]: g for g in (genomes or [])}
    questions = [q for q in bank["questions"] if q["source"]["origin"] != "generated"]
    if not questions:
        raise ValueError("no source questions to analyze (generated questions are excluded)")

    by_paper: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for q in questions:
        by_paper[q["source"]["document"] or "(unknown document)"].append(q)
    for qs in by_paper.values():
        qs.sort(key=lambda q: q["source"].get("position") or 0)

    difficulty = {q["id"]: question_difficulty(q, genome_by_q.get(q["id"])) for q in questions}

    papers = []
    for name, qs in sorted(by_paper.items()):
        complete = all(q["marks"] is not None for q in qs)
        sections: Dict[str, Dict[str, Any]] = {}
        for q in qs:
            label = q.get("section") or "(none)"
            sec = sections.setdefault(label, {"label": label, "question_ids": [], "marks": 0, "marks_complete": True})
            sec["question_ids"].append(q["id"])
            if q["marks"] is None:
                sec["marks_complete"] = False
            else:
                sec["marks"] += q["marks"]
        papers.append(
            {
                "document": name,
                "question_count": len(qs),
                "total_marks": sum(q["marks"] for q in qs) if complete else None,
                "marks_complete": complete,
                "section_order": list(sections.keys()),
                "sections": list(sections.values()),
                "ordering": [
                    {"id": q["id"], "section": q.get("section"), "type": q.get("question_type"), "marks": q["marks"]} for q in qs
                ],
            }
        )

    complete_papers = [p for p in papers if p["marks_complete"]]
    mark_values = [q["marks"] for q in questions if q["marks"] is not None]

    # Section definitions aggregated across papers.
    section_labels: List[str] = []
    for p in papers:
        for label in p["section_order"]:
            if label not in section_labels:
                section_labels.append(label)
    section_defs = []
    total_marks_all = sum(p["total_marks"] for p in complete_papers) or 0
    for label in section_labels:
        sec_qs = [q for q in questions if (q.get("section") or "(none)") == label]
        per_paper_marks = [s["marks"] for p in papers for s in p["sections"] if s["label"] == label and s["marks_complete"]]
        per_paper_counts = [len(s["question_ids"]) for p in papers for s in p["sections"] if s["label"] == label]
        sec_marks_complete = sum(s["marks"] for p in complete_papers for s in p["sections"] if s["label"] == label)
        section_defs.append(
            {
                "label": label,
                "papers_present": sum(1 for p in papers if label in p["section_order"]),
                "question_count": summary(per_paper_counts),
                "marks": summary(per_paper_marks),
                "mark_share": round(sec_marks_complete / total_marks_all, 4) if total_marks_all else None,
                "marks_per_question": summary([q["marks"] for q in sec_qs if q["marks"] is not None]),
                "question_types": frequency(q.get("question_type") for q in sec_qs),
                "evidence": [q["id"] for q in sec_qs],
            }
        )

    # Sequencing patterns.
    nondecreasing = {}
    for label in section_labels:
        checks = []
        for p in papers:
            marks_seq = [o["marks"] for o in p["ordering"] if (o["section"] or "(none)") == label]
            if len(marks_seq) >= 2 and None not in marks_seq:
                checks.append(all(a <= b for a, b in zip(marks_seq, marks_seq[1:])))
        nondecreasing[label] = {"papers_checked": len(checks), "papers_nondecreasing": sum(checks)}
    orders = frequency(" > ".join(p["section_order"]) for p in papers)

    # Concept combinations from genomes (primary + secondary concepts in one question).
    combos: Dict[tuple, List[str]] = defaultdict(list)
    for q in questions:
        g = genome_by_q.get(q["id"])
        if not g:
            continue
        k = g["knowledge"]
        concepts = sorted({c for c in [k.get("primary_concept"), *(k.get("secondary_concepts") or [])] if c})
        for pair in combinations(concepts, 2):
            combos[pair].append(q["id"])
    concept_combinations = [
        {"concepts": list(pair), "count": len(ids), "evidence": ids} for pair, ids in sorted(combos.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    ][:50]

    n_papers = len(papers)
    level = evidence_level(n_papers)
    notes = []
    if level in ("insufficient", "limited"):
        notes.append(
            f"Blueprint is based on {n_papers} paper(s); treat distributions as a low-confidence approximation, not a stable pattern."
        )
    missing_marks = [q["id"] for q in questions if q["marks"] is None]
    if missing_marks:
        notes.append(f"{len(missing_marks)} question(s) have no mark allocation; mark-based statistics exclude them.")
    no_topic = [q["id"] for q in questions if not q.get("topic")]
    if no_topic:
        notes.append(f"{len(no_topic)} question(s) have no topic label.")
    no_diff = [qid for qid, d in difficulty.items() if d["points"] is None]
    if no_diff:
        notes.append(f"Difficulty features unavailable for {len(no_diff)} question(s).")
    if not genomes:
        notes.append("No genomes supplied: concept combinations and genome-based difficulty are unavailable.")
    low_conf = [q["id"] for q in questions if q.get("extraction_confidence") == "low"]
    if low_conf:
        notes.append(f"{len(low_conf)} question(s) were extracted with low confidence.")

    target_total = median([p["total_marks"] for p in complete_papers]) if complete_papers else None
    profile = {
        "schema_version": SCHEMA_VERSION,
        "profile_id": stable_id("dna", sorted(q["id"] for q in questions)),
        "source_set": {
            "bank_id": bank.get("bank_id"),
            "documents": [d for d in bank.get("source_documents", [])],
            "paper_count": n_papers,
            "question_count": len(questions),
            "subjects": frequency(q.get("subject") for q in questions),
        },
        "papers": papers,
        "aggregate": {
            "questions_per_paper": summary([p["question_count"] for p in papers]),
            "marks_per_paper": summary([p["total_marks"] for p in complete_papers]),
            "marks_per_question": summary(mark_values),
        },
        "distributions": {
            "topic": _weighted(questions, lambda q: [q["topic"]] if q.get("topic") else []),
            "subtopic": _weighted(questions, lambda q: [q["subtopic"]] if q.get("subtopic") else []),
            "question_type": _weighted(questions, lambda q: [q["question_type"]] if q.get("question_type") else []),
            "cognitive_level": _weighted(questions, lambda q: [q["cognitive_level"]] if q.get("cognitive_level") else []),
            "learning_objective": _weighted(questions, lambda q: q.get("learning_objectives") or []),
            "difficulty_band": _weighted(questions, lambda q: [difficulty[q["id"]]["band"]] if difficulty[q["id"]]["band"] else []),
        },
        "sections": section_defs,
        "sequencing": {"section_orders": orders, "marks_nondecreasing_within_section": nondecreasing},
        "concept_combinations": concept_combinations,
        "structural_constraints": {
            "target_total_marks": int(target_total) if target_total is not None else None,
            "target_question_count": median([p["question_count"] for p in papers]),
            "section_order": section_labels,
            "section_mark_share": {s["label"]: s["mark_share"] for s in section_defs},
            "basis": "median of complete source papers",
        },
        "uncertainty": {
            "paper_count": n_papers,
            "evidence_level": level,
            "questions_missing_marks": missing_marks,
            "questions_low_confidence": low_conf,
            "questions_without_difficulty": no_diff,
            "notes": notes,
        },
        "evidence": {
            "per_question_difficulty": difficulty,
            "provenance_counts": frequency(v for q in questions for v in q.get("provenance", {}).values()),
        },
        "classification_schema": {
            "question_types": QUESTION_TYPES,
            "cognitive_levels": COGNITIVE_LEVELS,
            "difficulty_bands": DIFFICULTY_BANDS,
            "representations": REPRESENTATIONS,
            "reasoning_step_types": REASONING_STEP_TYPES,
        },
        "difficulty_model": DIFFICULTY_MODEL,
        "generation_preferences": {"mode": "balanced", "seed": 0, **(preferences or {})},
    }
    errors = validate(profile, "exam_dna")
    if errors:  # pragma: no cover - guards against developer error
        raise ValueError("internal error: exam DNA profile failed schema: " + "; ".join(errors))
    return profile
