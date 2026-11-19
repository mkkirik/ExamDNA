"""End-to-end demonstration on the original synthetic physics dataset.

Writes everything to examples/expected_outputs/demo_workspace/ (that folder is
deleted and recreated). The deterministic outputs are reproducible: running
this twice produces identical files.

Steps
  1. build the synthetic dataset (tools/build_synthetic_dataset.py)
  2. ingest the structured bank, plus a text-parser ingestion of paper1.md
  3. prepare: genomes + Exam DNA + mutation plan
  4. "agent" step: write candidates for the plan (tools/build_demo_candidates.py)
  5. finish: validate, compile, render, report
  6. extras: harder exam, infeasible config diagnosis, 5-variant plan,
     generation-2 mutation, baseline comparison
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import build_demo_candidates  # noqa: E402
import build_synthetic_dataset  # noqa: E402
from examdna.compiler import CompilationInfeasible, compile_exam  # noqa: E402
from examdna.evaluation import compare, comparison_markdown  # noqa: E402
from examdna.extraction.loaders import load_source  # noqa: E402
from examdna.mutation import build_lineage, plan_mutations, plan_variants  # noqa: E402
from examdna.reporting import (  # noqa: E402
    answer_key_markdown,
    comparison_report_markdown,
    exam_html,
    exam_markdown,
    lineage_report_markdown,
    marking_guide_markdown,
    validation_summary_markdown,
)
from examdna.utilities.io import read_json_file, write_json, write_text  # noqa: E402
from examdna.validation import validate_candidates  # noqa: E402
from examdna.workflow import finish, prepare  # noqa: E402

INPUTS = ROOT / "examples" / "synthetic_inputs"
WS = ROOT / "examples" / "expected_outputs" / "demo_workspace"
DEMO_QUESTIONS = "p1-a2,p1-a3,p1-a4,p1-a6,p2-a2,p2-a3,p2-a4,p2-a5,p3-a2,p3-a3,p3-a4,p1-b1,p1-b2,p1-b3,p2-b1,p2-b3,p3-b1,p3-b2".split(",")


def gen2_candidate(spec):
    """Agent output for the generation-2 parameter mutation (authored after reading the spec)."""
    change = spec["parameters"]["changes"][0]
    assert change["symbol"] == "t" and change["suggested"] == 2.5, "demo spec changed; re-author the generation-2 candidate"
    qid = "m2-p1-a2-rep-par"
    q = build_demo_candidates.question(
        qid, "Kinematics", "Uniform acceleration", "calculation", 2, "A",
        "A sprinter's velocity–time graph during the drive phase is shown below. Using the graph, find the sprinter's acceleration.",
        los=["K1", "K2"], cognitive="application",
        given=[build_demo_candidates.g("v", 9.0, "m/s", "velocity at 2.5 s (read from graph)"), build_demo_candidates.g("t", 2.5, "s", "time (read from graph)")],
        diagram="Velocity–time graph: v / m s⁻¹ (vertical, 0 to 10) against t / s (horizontal, 0 to 3). A straight line runs from (0 s, 0 m/s) to (2.5 s, 9.0 m/s).",
        final="3.6 m/s²", worked="a = gradient = 9.0/2.5 = 3.6 m/s²",
        points=[("Acceleration = gradient", 1), ("3.6 m/s²", 1)],
    )
    gnm = build_demo_candidates.genome(
        qid, "uniform acceleration", secondary=["velocity", "gradient"], prereq=["velocity"], los=["K1", "K2"], context="sports and athletics",
        reasoning=build_demo_candidates.lin("read_representation", "select_relation", "apply_mathematics", "derive_result"), rep=("verbal", "graph"), math=1,
    )
    return {
        "candidate_id": "g2-c01", "spec_id": spec["spec_id"], "parent_id": spec["parent_id"], "operator": "parameter",
        "question": q, "genome": gnm,
        "verification": build_demo_candidates.num("v/t", {"v": 9.0, "t": 2.5}, 3.6, "m/s^2"),
        "invariant_judgements": build_demo_candidates.judge(), "change_summary": "Time read from the graph changed to 2.5 s; answer recomputed.",
    }


def main() -> int:
    build_synthetic_dataset.main()
    if WS.exists():
        shutil.rmtree(WS)
    WS.mkdir(parents=True)

    # 2. ingestion
    bank = load_source(INPUTS / "physics_bank.json")
    write_json(WS / "bank.json", bank)
    write_json(WS / "extras" / "paper1_text_ingest.json", load_source(INPUTS / "paper1.md", subject="Introductory Physics"))
    shutil.copyfile(INPUTS / "annotations.json", WS / "annotations.json")

    # 3. prepare
    prep = prepare(WS, mode="balanced", per_question=1, seed=7, questions=DEMO_QUESTIONS)

    # 4. agent step (fixture)
    build_demo_candidates.main(["build_demo_candidates.py", str(WS)])

    # 5. finish
    shutil.copyfile(INPUTS / "compile_config.json", WS / "compile_config.json")
    result = finish(WS)
    if result["status"] != "compiled":
        print(json.dumps(result, indent=2))
        return 1

    pool = read_json_file(WS / "validated_pool.json")
    dna = read_json_file(WS / "exam_dna.json")
    genomes = read_json_file(WS / "genomes.json")["genomes"]

    # 6a. harder exam
    harder_cfg = read_json_file(INPUTS / "compile_config_harder.json")
    harder = compile_exam(pool, harder_cfg, dna)
    write_json(WS / "extras" / "exam_harder.json", harder)
    write_text(WS / "extras" / "harder" / "exam.md", exam_markdown(harder))
    write_text(WS / "extras" / "harder" / "exam.html", exam_html(harder))
    write_text(WS / "extras" / "harder" / "answer_key.md", answer_key_markdown(harder))
    write_text(WS / "extras" / "harder" / "exam_vs_dna.md", comparison_report_markdown(harder, dna))

    # 6b. infeasible configuration
    try:
        compile_exam(pool, read_json_file(INPUTS / "compile_config_conflict.json"), dna)
        print("expected the conflict configuration to be infeasible")
        return 1
    except CompilationInfeasible as exc:
        write_json(WS / "extras" / "conflict_diagnosis.json", exc.diagnosis)

    # 6c. five structurally different variants of one question
    write_json(WS / "extras" / "variants_plan_p1-b2.json", plan_variants(bank, genomes, "p1-b2", 5, mode="exploratory", seed=7))

    # 6d. generation 2: mutate an accepted generated question again
    merged = dict(bank, questions=bank["questions"] + pool["questions"])
    merged_genomes = genomes + pool["extensions"]["genomes"]
    plan2 = plan_mutations(merged, merged_genomes, question_ids=["m-p1-a2-rep"], operators=["parameter"], seed=7)
    cand2 = gen2_candidate(plan2["specs"][0])
    report2, pool2 = validate_candidates([cand2], plan2, merged, merged_genomes)
    g2 = WS / "extras" / "generation2"
    write_json(g2 / "mutation_plan.json", plan2)
    write_json(g2 / "candidates.json", {"candidates": [cand2]})
    write_json(g2 / "validation_report.json", report2)
    write_json(g2 / "validated_pool.json", pool2)
    write_text(g2 / "validation_summary.md", validation_summary_markdown(report2))
    lineage = build_lineage(bank["questions"] + pool["questions"] + pool2["questions"])
    write_text(g2 / "lineage_report.md", lineage_report_markdown(lineage))

    # 6e. baseline comparison (illustrative baseline fixture, not experimental data)
    cmp = compare(
        read_json_file(INPUTS / "baseline_naive_exam.json"),
        read_json_file(WS / "exam.json"),
        read_json_file(WS / "compile_config.json"),
        source_bank=bank,
        validation_report=read_json_file(WS / "validation_report.json"),
    )
    write_json(WS / "extras" / "baseline_comparison.json", cmp)
    write_text(WS / "extras" / "baseline_comparison.md", comparison_markdown(cmp, baseline_label="Illustrative baseline fixture"))

    summary = {
        "prepare": prep,
        "finish": result["summary"],
        "exam_id": result["exam_id"],
        "harder_exam_id": harder["exam_id"],
        "generation2": report2["summary"],
        "lineage_max_generation": lineage["max_generation"],
    }
    write_json(WS / "extras" / "demo_summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
