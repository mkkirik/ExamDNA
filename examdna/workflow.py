"""Two-call workspace workflow used by the Skill.

``prepare``  bank.json (+ annotations.json) → genomes.json, exam_dna.json,
             mutation_plan.json, reports/exam_dna_report.md
             (then the agent writes candidates.json from the plan)
``finish``   candidates.json + compile_config.json → validation report,
             validated pool, exam.json, rendered exam, answer key, marking
             guide and all reports

Everything is deterministic given the workspace files and the seed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .compiler import CompilationInfeasible, compile_exam
from .fingerprint import analyze_bank
from .genome import build_genomes
from .mutation import build_lineage, plan_mutations
from .reporting import (
    analysis_report_markdown,
    answer_key_markdown,
    comparison_report_markdown,
    dna_report_markdown,
    exam_html,
    exam_markdown,
    lineage_report_markdown,
    marking_guide_markdown,
    validation_summary_markdown,
)
from .utilities.io import InputError, read_json_file, write_json, write_text
from .validation import validate_candidates

FILES = {
    "bank": "bank.json",
    "annotations": "annotations.json",
    "genomes": "genomes.json",
    "dna": "exam_dna.json",
    "plan": "mutation_plan.json",
    "candidates": "candidates.json",
    "report": "validation_report.json",
    "pool": "validated_pool.json",
    "config": "compile_config.json",
    "exam": "exam.json",
    "diagnosis": "compile_diagnosis.json",
}


def _p(ws: Path, key: str) -> Path:
    return ws / FILES[key]


def _load(ws: Path, key: str, required: bool = True) -> Optional[Any]:
    path = _p(ws, key)
    if not path.exists():
        if required:
            raise InputError(f"workspace is missing {FILES[key]}")
        return None
    return read_json_file(path)


def prepare(
    workspace: str | Path,
    *,
    mode: str = "balanced",
    per_question: int = 2,
    seed: int = 0,
    operators: Optional[Sequence[str]] = None,
    questions: Optional[Sequence[str]] = None,
    difficulty_direction: str = "up",
) -> Dict[str, Any]:
    ws = Path(workspace)
    bank = _load(ws, "bank")
    annotations = _load(ws, "annotations", required=False)
    genomes_doc = build_genomes(bank, annotations)
    write_json(_p(ws, "genomes"), genomes_doc)
    dna = analyze_bank(bank, genomes_doc["genomes"], preferences={"mode": mode, "seed": seed})
    write_json(_p(ws, "dna"), dna)
    write_text(ws / "reports" / "exam_dna_report.md", dna_report_markdown(dna))
    plan = plan_mutations(
        bank,
        genomes_doc["genomes"],
        question_ids=questions,
        operators=operators,
        mode=mode,
        per_question=per_question,
        seed=seed,
        difficulty_direction=difficulty_direction,
    )
    write_json(_p(ws, "plan"), plan)
    return {
        "genomes": genomes_doc["report"],
        "evidence_level": dna["uncertainty"]["evidence_level"],
        "uncertainty_notes": dna["uncertainty"]["notes"],
        "specs": len(plan["specs"]),
        "skipped": len(plan["skipped"]),
        "next_step": f"Write {FILES['candidates']} (one candidate per spec in {FILES['plan']}), and {FILES['config']}, then run 'finish'.",
    }


def finish(workspace: str | Path, *, output_dir: Optional[str | Path] = None, seed: Optional[int] = None) -> Dict[str, Any]:
    ws = Path(workspace)
    out = Path(output_dir) if output_dir else ws / "output"
    bank = _load(ws, "bank")
    genomes_doc = _load(ws, "genomes")
    plan = _load(ws, "plan")
    cands_doc = _load(ws, "candidates")
    candidates = cands_doc.get("candidates", cands_doc) if isinstance(cands_doc, dict) else cands_doc
    if not isinstance(candidates, list):
        raise InputError("candidates.json must be a list or {\"candidates\": [...]}")
    dna = _load(ws, "dna", required=False)
    config = _load(ws, "config")
    if seed is not None:
        config["seed"] = seed

    report, pool = validate_candidates(candidates, plan, bank, genomes_doc["genomes"])
    write_json(_p(ws, "report"), report)
    write_json(_p(ws, "pool"), pool)
    write_text(ws / "reports" / "validation_summary.md", validation_summary_markdown(report))
    lineage = build_lineage(bank["questions"] + pool["questions"])
    write_json(ws / "reports" / "lineage.json", lineage)

    summary: Dict[str, Any] = {
        "source_documents": len(bank.get("source_documents", [])),
        "extracted_questions": len(bank["questions"]),
        "genomes_complete": sum(1 for g in genomes_doc["genomes"] if g["validation"]["structural_completeness"] == "complete"),
        "mutation_specs": len(plan["specs"]),
        "candidates": report["summary"]["candidates"],
        "passed": report["summary"]["PASS"],
        "review_required": report["summary"]["REVIEW_REQUIRED"],
        "rejected": report["summary"]["FAIL"],
    }
    try:
        exam = compile_exam(pool, config, dna)
    except CompilationInfeasible as exc:
        write_json(_p(ws, "diagnosis"), exc.diagnosis)
        write_text(ws / "reports" / "lineage_report.md", lineage_report_markdown(lineage))
        summary["compiled_questions"] = 0
        summary["deviations"] = [f"Compilation infeasible: {exc.diagnosis['message']}"] + exc.diagnosis["suggestions"]
        write_text(ws / "reports" / "analysis_report.md", analysis_report_markdown(summary))
        return {"status": "infeasible", "diagnosis": exc.diagnosis, "summary": summary}

    write_json(_p(ws, "exam"), exam)
    write_text(out / "exam.md", exam_markdown(exam))
    write_text(out / "exam.html", exam_html(exam))
    write_text(out / "answer_key.md", answer_key_markdown(exam))
    write_text(out / "marking_guide.md", marking_guide_markdown(exam))
    write_text(ws / "reports" / "lineage_report.md", lineage_report_markdown(lineage, exam))
    write_text(ws / "reports" / "exam_vs_dna.md", comparison_report_markdown(exam, dna))
    summary["compiled_questions"] = exam["question_count"]
    deviations: List[str] = []
    for dim, tv in exam["properties"]["deviation_total_variation"].items():
        if dim in ("family_repeat", "question_count"):
            continue
        if exam["properties"]["targets"].get(dim) and tv > 0.25:
            deviations.append(f"{dim}: total-variation distance {tv} from the blueprint target")
    count_target = (exam["properties"]["targets"].get("question_count") or {}).get("n")
    if count_target and abs(exam["question_count"] - count_target) >= 2:
        deviations.append(f"question count {exam['question_count']} vs blueprint-scaled target {count_target}")
    if exam["properties"]["review_required_questions"]:
        deviations.append(f"{len(exam['properties']['review_required_questions'])} REVIEW_REQUIRED question(s) included (flagged in answer key).")
    summary["deviations"] = deviations or ["None above the 0.25 total-variation reporting threshold."]
    summary["limitations"] = [
        "Difficulty bands are heuristic and not calibrated on student data.",
        "Semantic checks marked model_assisted rely on the agent's own judgement.",
        f"Blueprint evidence level: {(dna or {}).get('uncertainty', {}).get('evidence_level', 'no blueprint')}.",
        "Solver optimality: " + exam["solver"]["optimality"] + ".",
    ]
    write_text(ws / "reports" / "analysis_report.md", analysis_report_markdown(summary))
    return {
        "status": "compiled",
        "exam_id": exam["exam_id"],
        "outputs": {
            "exam_markdown": str(out / "exam.md"),
            "exam_html": str(out / "exam.html"),
            "answer_key": str(out / "answer_key.md"),
            "marking_guide": str(out / "marking_guide.md"),
            "exam_json": str(_p(ws, "exam")),
            "reports": str(ws / "reports"),
        },
        "summary": summary,
    }
