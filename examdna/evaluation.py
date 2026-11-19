"""Observable-property comparison between a baseline exam and an ExamDNA exam.

This does not measure educational quality. It counts properties that can be
read off the two artifacts: field completeness, mark compliance, section
adherence, explicit objective coverage, lineage, duplication, verification
evidence and copying from sources. See docs/evaluation.md for the protocol.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .mutation.properties import full_text
from .utilities.stats import surface_similarity, total_variation

REQUIRED_FIELDS = ["text", "marks", "topic", "question_type", "learning_objectives", "answer"]


def _flatten(exam: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "sections" in exam and exam["sections"] and "questions" in exam["sections"][0]:
        out = []
        for s in exam["sections"]:
            for item in s["questions"]:
                q = dict(item.get("question", item))
                q.setdefault("section", s["label"])
                q["_section"] = s["label"]
                q["_state"] = item.get("validation_state")
                out.append(q)
        return out
    return [dict(q, _section=q.get("section")) for q in exam.get("questions", [])]


def _has_answer(q: Dict[str, Any]) -> bool:
    m = q.get("marking") or {}
    return bool(q.get("answer") or m.get("final_answer") or m.get("answer_key") or m.get("points"))


def evaluate_exam(
    exam: Dict[str, Any],
    config: Dict[str, Any],
    *,
    source_bank: Optional[Dict[str, Any]] = None,
    validation_report: Optional[Dict[str, Any]] = None,
    section_targets: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    qs = _flatten(exam)
    n = len(qs)
    complete = 0
    missing_by_field = {f: 0 for f in REQUIRED_FIELDS}
    for q in qs:
        ok = True
        for f in REQUIRED_FIELDS:
            present = _has_answer(q) if f == "answer" else bool(q.get(f))
            if not present:
                missing_by_field[f] += 1
                ok = False
        complete += ok
    marks = [q.get("marks") for q in qs]
    known = [m for m in marks if isinstance(m, int)]
    total = sum(known)
    marks_complete = len(known) == n
    if section_targets is None:
        section_targets = {s["label"]: s["marks"] for s in config.get("sections") or []}
    actual_sections: Dict[str, int] = {}
    for q in qs:
        if isinstance(q.get("marks"), int):
            label = q.get("_section") or "(none)"
            actual_sections[label] = actual_sections.get(label, 0) + q["marks"]
    section_tv = total_variation(actual_sections, section_targets) if section_targets else None
    los = sorted({lo for q in qs for lo in q.get("learning_objectives") or []})

    source_ids = {q["id"] for q in (source_bank or {}).get("questions", [])}
    with_lineage = [q for q in qs if (q.get("lineage") or {}).get("parent_id")]
    valid_lineage = [q for q in with_lineage if not source_ids or q["lineage"].get("root_id") in source_ids or q["lineage"]["parent_id"] in source_ids]

    texts = [full_text(q) if q.get("text") else "" for q in qs]
    dup_pairs = sum(1 for i in range(n) for j in range(i + 1, n) if surface_similarity(texts[i], texts[j]) >= 0.8)
    source_texts = [full_text(q) for q in (source_bank or {}).get("questions", [])]
    copies = sum(1 for t in texts if any(surface_similarity(t, s) >= 0.85 for s in source_texts)) if source_texts else None
    numeric_verified = sum(1 for q in qs if (q.get("validation") or {}).get("numeric_verified"))
    states = {}
    for q in qs:
        st = q.get("_state") or (q.get("validation") or {}).get("state") or "none"
        states[st] = states.get(st, 0) + 1

    return {
        "question_count": n,
        "required_field_completeness": {"complete_questions": complete, "of": n, "missing_by_field": missing_by_field},
        "total_marks": {"requested": config.get("total_marks"), "actual_known": total, "all_marks_known": marks_complete, "compliant": marks_complete and total == config.get("total_marks")},
        "section_adherence": {"targets": section_targets, "actual": actual_sections, "total_variation": section_tv},
        "explicit_learning_objectives": {"distinct": len(los), "questions_with_objectives": sum(1 for q in qs if q.get("learning_objectives"))},
        "lineage": {"questions_with_lineage": len(with_lineage), "lineage_resolves_to_source": len(valid_lineage)},
        "surface_duplicate_pairs": dup_pairs,
        "near_verbatim_source_copies": copies,
        "numeric_solutions_recomputed": numeric_verified,
        "validation_states": states,
        "validation_failures_identified": (validation_report or {}).get("summary", {}).get("FAIL"),
    }


def compare(baseline: Dict[str, Any], examdna_exam: Dict[str, Any], config: Dict[str, Any], **kw) -> Dict[str, Any]:
    validation_report = kw.pop("validation_report", None)
    targets = {s["label"]: s["marks"] for s in config.get("sections") or []}
    basis = "compile configuration"
    if not targets and examdna_exam.get("sections"):
        targets = {s["label"]: s["marks"] for s in examdna_exam["sections"]}
        basis = "blueprint-derived sections of the ExamDNA exam"
    return {
        "note": "Observable properties of two artifacts. Not a measure of educational quality or learning outcomes.",
        "section_target_basis": basis,
        "baseline": evaluate_exam(baseline, config, section_targets=targets, **kw),
        "examdna": evaluate_exam(examdna_exam, config, validation_report=validation_report, section_targets=targets, **kw),
    }


def comparison_markdown(result: Dict[str, Any], baseline_label: str = "Baseline") -> str:
    b, e = result["baseline"], result["examdna"]

    def row(name, f):
        return f"| {name} | {f(b)} | {f(e)} |"

    lines = [
        "# Baseline vs. ExamDNA — observable properties",
        "",
        f"> {result['note']}",
        "",
        f"| Property | {baseline_label} | ExamDNA |",
        "| --- | --- | --- |",
        row("Questions", lambda x: x["question_count"]),
        row("Questions with all required fields", lambda x: f"{x['required_field_completeness']['complete_questions']}/{x['required_field_completeness']['of']}"),
        row("Total marks (requested → actual)", lambda x: f"{x['total_marks']['requested']} → {x['total_marks']['actual_known']}{'' if x['total_marks']['all_marks_known'] else ' (some unknown)'}"),
        row("Mark total compliant", lambda x: "yes" if x["total_marks"]["compliant"] else "no"),
        row("Section distribution TV distance", lambda x: x["section_adherence"]["total_variation"] if x["section_adherence"]["total_variation"] is not None else "n/a"),
        row("Distinct explicit learning objectives", lambda x: x["explicit_learning_objectives"]["distinct"]),
        row("Questions with lineage to a source", lambda x: x["lineage"]["lineage_resolves_to_source"]),
        row("Surface-duplicate pairs", lambda x: x["surface_duplicate_pairs"]),
        row("Near-verbatim source copies", lambda x: "n/a" if x["near_verbatim_source_copies"] is None else x["near_verbatim_source_copies"]),
        row("Numeric solutions recomputed", lambda x: x["numeric_solutions_recomputed"]),
        row("Validation failures identified", lambda x: "n/a" if x["validation_failures_identified"] is None else x["validation_failures_identified"]),
        "",
    ]
    return "\n".join(lines)
