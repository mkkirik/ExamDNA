"""Integration tests A–G plus CLI and reproducibility checks, on synthetic data."""

import contextlib
import copy
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from tests.helpers import DEMO_QUESTIONS, INPUTS, ROOT, bank, demo_candidates, genomes
from examdna.cli import main as cli_main
from examdna.compiler import CompilationInfeasible, compile_exam
from examdna.fingerprint import analyze_bank
from examdna.genome import build_genomes, check_genome
from examdna.models.schema import validate
from examdna.mutation import build_lineage, plan_mutations
from examdna.utilities.io import read_json_file, write_json
from examdna.validation import validate_candidates


def run_cli(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = cli_main([str(a) for a in args])
    return code, out.getvalue()


class DemoPipeline:
    """Round-1 demo pipeline computed once per test class."""

    _cache = None

    @classmethod
    def get(cls):
        if cls._cache is None:
            b, g = bank(), genomes()
            plan = plan_mutations(b, g, question_ids=DEMO_QUESTIONS, mode="balanced", per_question=1, seed=7)
            cands = demo_candidates(plan)
            report, pool = validate_candidates(cands, plan, b, g)
            cls._cache = (b, g, plan, cands, report, pool)
        return copy.deepcopy(cls._cache)


class TestA_Analysis(unittest.TestCase):
    def test_exam_dna_profile(self):
        dna = analyze_bank(bank(), genomes())
        self.assertEqual(dna["source_set"]["paper_count"], 3)
        self.assertEqual(dna["source_set"]["question_count"], 27)
        self.assertEqual(dna["structural_constraints"]["section_order"], ["A", "B"])
        self.assertTrue(dna["concept_combinations"])
        for d in dna["distributions"].values():
            for cat, ids in d["evidence"].items():
                self.assertEqual(len(ids), d["counts"][cat])


class TestB_Genome(unittest.TestCase):
    def test_genome_construction_and_schema(self):
        doc = build_genomes(bank(), read_json_file(INPUTS / "annotations.json"))
        self.assertEqual(doc["report"]["count"], 27)
        self.assertEqual(doc["report"]["errors"], {})
        for g in doc["genomes"]:
            self.assertEqual(check_genome(g), [])

    def test_annotation_for_unknown_question_rejected(self):
        from examdna.utilities.io import InputError

        with self.assertRaises(InputError):
            build_genomes(bank(), {"annotations": {"ghost": {}}})


class TestC_Mutation(unittest.TestCase):
    def test_plan_candidates_validation(self):
        b, g, plan, cands, report, pool = DemoPipeline.get()
        self.assertEqual(len(plan["specs"]), 18)
        self.assertEqual(report["summary"], {"candidates": 22, "PASS": 17, "REVIEW_REQUIRED": 1, "FAIL": 4})
        self.assertEqual(len(pool["questions"]), 18)
        for q in pool["questions"]:
            self.assertEqual(validate(q, "question"), [])
            self.assertEqual(q["source"]["origin"], "generated")
            self.assertIn(q["lineage"]["parent_id"], {x["id"] for x in b["questions"]})
        lin = build_lineage(b["questions"] + pool["questions"])
        self.assertTrue(lin["valid"], lin["errors"])


class TestE_Rejection(unittest.TestCase):
    def test_known_invalid_candidates_fail_for_the_right_reason(self):
        *_, report, _ = DemoPipeline.get()
        by_id = {r["candidate_id"]: r for r in report["results"]}
        expect = {
            "c04-try1": "preserve:numeric_parameters",
            "c06-try1": "source_copy",
            "c12-try1": "recompute",
            "c14-try1": "uniqueness",
        }
        for cid, check in expect.items():
            r = by_id[cid]
            self.assertEqual(r["state"], "FAIL", cid)
            self.assertIn(check, [c["check"] for c in r["checks"] if c["status"] == "FAIL"], cid)
        self.assertEqual(by_id["c11"]["state"], "REVIEW_REQUIRED")

    def test_malformed_and_mismatched_candidates(self):
        b, g, plan, cands, *_ = DemoPipeline.get()
        good = cands[0]
        bad_schema = {"candidate_id": "z1"}
        wrong_spec = dict(copy.deepcopy(good), candidate_id="z2", spec_id="spec-doesnotexist")
        wrong_op = dict(copy.deepcopy(good), candidate_id="z3", operator="surface")
        contradictory = copy.deepcopy(good)
        contradictory["candidate_id"] = "z4"
        contradictory["question"]["id"] = "m-z4"
        contradictory["question"]["constraints"] = [{"text": "v > 10", "var": "v", "op": ">", "value": 10}, {"text": "v < 5", "var": "v", "op": "<", "value": 5}]
        report, pool = validate_candidates([bad_schema, wrong_spec, wrong_op, contradictory], plan, b, g)
        states = {r["candidate_id"]: r["state"] for r in report["results"]}
        self.assertEqual(states, {"z1": "FAIL", "z2": "FAIL", "z3": "FAIL", "z4": "FAIL"})
        self.assertEqual(pool["questions"], [])


class TestD_Compilation(unittest.TestCase):
    def test_compile_from_validated_pool(self):
        b, g, plan, cands, report, pool = DemoPipeline.get()
        dna = analyze_bank(b, g)
        cfg = read_json_file(INPUTS / "compile_config.json")
        exam = compile_exam(pool, cfg, dna)
        self.assertEqual(exam["total_marks"], 30)
        self.assertEqual([s["marks"] for s in exam["sections"]], [10, 20])
        for s in exam["sections"]:
            self.assertEqual(sum(q["marks"] for q in s["questions"]), s["marks"])
            for q in s["questions"]:
                self.assertEqual(q["validation_state"], "PASS")
                self.assertTrue(q["lineage"]["parent_id"])
        topics = {q["question"]["topic"] for s in exam["sections"] for q in s["questions"]}
        self.assertTrue({"Kinematics", "Electricity"} <= topics)
        roots = [q["lineage"]["root_id"] for s in exam["sections"] for q in s["questions"]]
        self.assertEqual(len(roots), len(set(roots)))
        self.assertEqual(exam, compile_exam(copy.deepcopy(pool), cfg, dna))  # reproducible

    def test_harder_config_raises_challenging_share(self):
        b, g, plan, cands, report, pool = DemoPipeline.get()
        dna = analyze_bank(b, g)
        normal = compile_exam(pool, read_json_file(INPUTS / "compile_config.json"), dna)
        harder = compile_exam(pool, read_json_file(INPUTS / "compile_config_harder.json"), dna)
        self.assertGreater(harder["properties"]["actual_mark_shares"]["difficulty"].get("challenging", 0), normal["properties"]["actual_mark_shares"]["difficulty"].get("challenging", 0))


class TestF_Infeasible(unittest.TestCase):
    def test_conflict_configuration(self):
        b, g, plan, cands, report, pool = DemoPipeline.get()
        with self.assertRaises(CompilationInfeasible) as ctx:
            compile_exam(pool, read_json_file(INPUTS / "compile_config_conflict.json"), analyze_bank(b, g))
        d = ctx.exception.diagnosis
        self.assertEqual(d["missing_required_types"], ["extended_response"])
        self.assertTrue(d["suggestions"])


class TestCLIAndWorkspace(unittest.TestCase):
    def test_cli_workspace_round_trip_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            code, _ = run_cli("ingest", INPUTS / "physics_bank.json", "--out", ws / "bank.json")
            self.assertEqual(code, 0)
            shutil.copyfile(INPUTS / "annotations.json", ws / "annotations.json")
            code, out = run_cli("prepare", "--workspace", ws, "--per-question", "1", "--seed", "7", "--questions", ",".join(DEMO_QUESTIONS))
            self.assertEqual(code, 0, out)
            plan = read_json_file(ws / "mutation_plan.json")
            write_json(ws / "candidates.json", {"candidates": demo_candidates(plan)})
            shutil.copyfile(INPUTS / "compile_config.json", ws / "compile_config.json")
            code, out = run_cli("finish", "--workspace", ws)
            self.assertEqual(code, 0, out)
            for rel in ("output/exam.md", "output/exam.html", "output/answer_key.md", "output/marking_guide.md", "reports/exam_dna_report.md",
                        "reports/validation_summary.md", "reports/lineage_report.md", "reports/exam_vs_dna.md", "reports/analysis_report.md", "exam.json"):
                self.assertTrue((ws / rel).is_file(), rel)
            first = (ws / "exam.json").read_bytes()
            code, _ = run_cli("finish", "--workspace", ws)
            self.assertEqual(first, (ws / "exam.json").read_bytes())
            # individual commands
            self.assertEqual(run_cli("analyze", "--bank", ws / "bank.json", "--genomes", ws / "genomes.json", "--out", ws / "dna2.json")[0], 0)
            self.assertEqual(run_cli("compare", "--genomes", ws / "genomes.json", "--a", "p1-a2", "--b", "p3-a3", "--bank", ws / "bank.json")[0], 0)
            self.assertEqual(run_cli("validate", "--bank", ws / "bank.json", "--out", ws / "bankcheck.json", "--summary", ws / "bankcheck.md")[0], 0)
            self.assertEqual(run_cli("mutation-plan", "--bank", ws / "bank.json", "--genomes", ws / "genomes.json", "--out", ws / "v.json", "--variants", "3", "--question", "p1-b1")[0], 0)
            self.assertEqual(run_cli("render", "--exam", ws / "exam.json", "--out-dir", ws / "tr", "--lang", "tr")[0], 0)
            self.assertIn("Toplam puan", (ws / "tr" / "exam.md").read_text(encoding="utf-8"))
            self.assertEqual(run_cli("lineage", "--bank", ws / "bank.json", "--pool", ws / "validated_pool.json")[0], 0)
            self.assertEqual(run_cli("evaluate", "--baseline", INPUTS / "baseline_naive_exam.json", "--exam", ws / "exam.json", "--config", ws / "compile_config.json",
                                     "--bank", ws / "bank.json", "--out", ws / "eval.json", "--markdown", ws / "eval.md")[0], 0)
            code, out = run_cli("compile", "--pool", ws / "validated_pool.json", "--config", INPUTS / "compile_config_conflict.json", "--out", ws / "x.json", "--diagnosis", ws / "diag.json")
            self.assertEqual(code, 2)
            self.assertTrue((ws / "diag.json").is_file())

    def test_cli_errors_are_clean(self):
        code, _ = run_cli("analyze", "--bank", "does-not-exist.json", "--out", "x.json")
        self.assertEqual(code, 1)
        self.assertEqual(run_cli("schema", "question")[0], 0)
        self.assertEqual(run_cli("operators")[0], 0)

    def test_module_invocation(self):
        proc = subprocess.run([sys.executable, "-m", "examdna.cli", "--version"], capture_output=True, text=True, cwd=ROOT, timeout=60)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("0.1.0", proc.stdout)
        proc = subprocess.run([sys.executable, str(ROOT / ".claude" / "skills" / "examdna" / "scripts" / "examdna_cli.py"), "--version"], capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class TestG_Packaging(unittest.TestCase):
    def test_build_and_verify_skill_archive(self):
        from examdna.packaging import build

        with tempfile.TemporaryDirectory() as tmp:
            result = build(Path(tmp))
            archive = Path(result["archive"])
            self.assertTrue(archive.is_file())
            with zipfile.ZipFile(archive) as zf:
                names = zf.namelist()
            self.assertIn("examdna/SKILL.md", names)
            self.assertIn("examdna/scripts/examdna_cli.py", names)
            self.assertIn("examdna/scripts/examdna/cli.py", names)
            self.assertIn("examdna/schemas/candidate.schema.json", names)
            self.assertIn("examdna/LICENSE.txt", names)
            self.assertFalse([n for n in names if "__pycache__" in n or n.endswith(".pyc") or "/tests/" in n or "/examples/" in n])
            self.assertEqual(result["verification"]["smoke_test"]["returncode"], 0)
            # deterministic archive
            again = build(Path(tmp) / "again", verify=False)
            self.assertEqual(result["sha256"], again["sha256"])


if __name__ == "__main__":
    unittest.main()
