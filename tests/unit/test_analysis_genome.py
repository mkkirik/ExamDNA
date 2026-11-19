import unittest

from tests.helpers import bank, genomes, mini_question
from examdna.extraction.normalize import normalize_bank
from examdna.fingerprint import analyze_bank
from examdna.fingerprint.difficulty import band_for, difficulty_points
from examdna.genome import analyze_reasoning_graph, build_genome, check_genome, compare_genomes
from examdna.genome.builder import detect_command_term
from examdna.models.schema import validate


class TestDifficulty(unittest.TestCase):
    def test_formula_and_bands(self):
        f = {"reasoning_stages": 3, "prerequisite_count": 2, "math_complexity": 1, "interacting_constraints": 0, "representation_count": 1}
        self.assertEqual(difficulty_points(f), 7)
        self.assertEqual(band_for(6), "foundation")
        self.assertEqual(band_for(7), "standard")
        self.assertEqual(band_for(13), "challenging")
        capped = {"reasoning_stages": 50, "prerequisite_count": 50, "math_complexity": 9, "interacting_constraints": 50, "representation_count": 50}
        self.assertEqual(difficulty_points(capped), 23)
        self.assertIsNone(difficulty_points({}))


class TestAnalyzer(unittest.TestCase):
    def setUp(self):
        self.dna = analyze_bank(bank(), genomes())

    def test_paper_totals_from_data(self):
        totals = sorted(p["total_marks"] for p in self.dna["papers"])
        self.assertEqual(totals, [30, 30, 32])
        self.assertEqual(self.dna["aggregate"]["marks_per_paper"]["median"], 30.0)
        self.assertEqual(self.dna["structural_constraints"]["target_total_marks"], 30)

    def test_distributions_match_manual_counts(self):
        b = bank()
        topic_counts = {}
        for q in b["questions"]:
            topic_counts[q["topic"]] = topic_counts.get(q["topic"], 0) + 1
        self.assertEqual(self.dna["distributions"]["topic"]["counts"], dict(sorted(topic_counts.items(), key=lambda kv: (-kv[1], kv[0]))))
        ev = self.dna["distributions"]["topic"]["evidence"]
        self.assertEqual(sum(len(v) for v in ev.values()), 27)

    def test_section_shares(self):
        shares = self.dna["structural_constraints"]["section_mark_share"]
        self.assertAlmostEqual(shares["A"] + shares["B"], 1.0, places=3)
        self.assertAlmostEqual(shares["A"], 32 / 92, places=3)

    def test_uncertainty_for_small_samples(self):
        self.assertEqual(self.dna["uncertainty"]["evidence_level"], "limited")
        one = normalize_bank([mini_question()])
        dna1 = analyze_bank(one)
        self.assertEqual(dna1["uncertainty"]["evidence_level"], "insufficient")
        self.assertTrue(any("No genomes" in n for n in dna1["uncertainty"]["notes"]))

    def test_missing_marks_excluded_and_noted(self):
        b = normalize_bank([mini_question(id="a"), mini_question(id="b", marks=None)])
        dna = analyze_bank(b)
        self.assertIsNone(dna["papers"][0]["total_marks"])
        self.assertTrue(any("no mark allocation" in n for n in dna["uncertainty"]["notes"]))

    def test_schema_valid(self):
        self.assertEqual(validate(self.dna, "exam_dna"), [])


class TestGenome(unittest.TestCase):
    def test_all_synthetic_genomes_valid_and_complete(self):
        for g in genomes():
            self.assertEqual(check_genome(g), [], g["question_id"])
            self.assertEqual(g["validation"]["structural_completeness"], "complete", g["question_id"])

    def test_missing_annotation_is_minimal_not_fabricated(self):
        q = normalize_bank([mini_question()])["questions"][0]
        g = build_genome(q)
        self.assertIsNone(g["knowledge"]["primary_concept"])
        self.assertEqual(g["validation"]["structural_completeness"], "minimal")
        self.assertIn("reasoning.steps", g["validation"]["missing_components"])
        self.assertEqual(g["assessment"]["command_term"], "calculate")
        self.assertEqual(g["field_provenance"]["assessment.command_term"], "calculated")

    def test_command_term_detection(self):
        self.assertEqual(detect_command_term("Explain why, then calculate x"), "explain")
        self.assertEqual(detect_command_term("Show that v = 3"), "show that")
        self.assertIsNone(detect_command_term("What is x?"))

    def test_graph_analysis(self):
        linear = analyze_reasoning_graph({"steps": [{"id": "a", "type": "read_given"}, {"id": "b", "type": "derive_result"}], "edges": [["a", "b"]]})
        self.assertTrue(linear["is_linear"])
        cyc = analyze_reasoning_graph({"steps": [{"id": "a", "type": "read_given"}, {"id": "b", "type": "derive_result"}], "edges": [["a", "b"], ["b", "a"]]})
        self.assertFalse(cyc["valid"])
        self.assertIn("cycle", cyc["errors"][0])
        branch = analyze_reasoning_graph(
            {"steps": [{"id": "a", "type": "read_given"}, {"id": "b", "type": "apply_mathematics"}, {"id": "c", "type": "justify"}], "edges": [["a", "b"], ["a", "c"]]}
        )
        self.assertEqual(branch["branch_points"], ["a"])
        self.assertFalse(branch["is_linear"])
        bad = analyze_reasoning_graph({"steps": [{"id": "a", "type": "read_given"}], "edges": [["a", "zz"]]})
        self.assertFalse(bad["valid"])

    def test_compare_self_and_different(self):
        gs = {g["question_id"]: g for g in genomes()}
        same = compare_genomes(gs["p1-a2"], gs["p1-a2"], "x y z w", "x y z w")["similarity"]
        self.assertTrue(all(v == 1.0 for v in same.values()))
        diff = compare_genomes(gs["p1-a2"], gs["p2-a6"])["similarity"]
        self.assertLess(diff["concept"], 0.5)
        self.assertLess(diff["answer"], 1.0)


if __name__ == "__main__":
    unittest.main()
