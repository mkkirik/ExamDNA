import copy
import unittest

from tests.helpers import bank, genomes
from examdna.models.schema import validate
from examdna.mutation import REGISTRY, build_lineage, find_duplicates, get_operator, plan_mutations, plan_variants, select_diverse
from examdna.mutation.distance import distance_profile, label
from examdna.mutation.planner import round_sig, significant_figures


class TestOperators(unittest.TestCase):
    def test_nine_operators_with_complete_contracts(self):
        self.assertEqual(len(REGISTRY), 9)
        for op in REGISTRY.values():
            c = op.contract()
            for key in ("id", "required_inputs", "preserve", "must_change", "invariants", "expected_difficulty_effect", "validation_checks", "failure_modes"):
                self.assertTrue(c[key], f"{op.id}.{key}")
            self.assertFalse(set(op.preserve) & set(op.must_change))

    def test_unknown_operator(self):
        with self.assertRaises(KeyError):
            get_operator("teleport")

    def test_applicability(self):
        q = {x["id"]: x for x in bank()["questions"]}
        g = {x["question_id"]: x for x in genomes()}
        self.assertFalse(get_operator("parameter").is_applicable(q["p1-a1"], g["p1-a1"])[0])  # no numeric givens
        self.assertTrue(get_operator("parameter").is_applicable(q["p1-a2"], g["p1-a2"])[0])
        self.assertFalse(get_operator("reasoning_path").is_applicable(q["p1-a1"], g["p1-a1"])[0])  # single step
        self.assertFalse(get_operator("constraint").is_applicable(q["p1-a5"], g["p1-a5"])[0])  # MC type


class TestPlanner(unittest.TestCase):
    def test_plan_is_reproducible(self):
        a = plan_mutations(bank(), genomes(), seed=3, per_question=2)
        b = plan_mutations(bank(), genomes(), seed=3, per_question=2)
        self.assertEqual(a, b)
        c = plan_mutations(bank(), genomes(), seed=4, per_question=2)
        self.assertNotEqual([s["spec_id"] for s in a["specs"]], [s["spec_id"] for s in c["specs"]])

    def test_specs_are_schema_valid_and_mode_respected(self):
        plan = plan_mutations(bank(), genomes(), mode="conservative", per_question=3, seed=1)
        allowed = {op.id for op in REGISTRY.values() if "conservative" in op.modes}
        for s in plan["specs"]:
            self.assertEqual(validate(s, "mutation_spec"), [])
            self.assertIn(s["operator"], allowed)
            self.assertIn("target_skill", s["required_judgements"])

    def test_requested_operator_not_in_mode_is_reported(self):
        plan = plan_mutations(bank(), genomes(), mode="conservative", operators=["reverse"], question_ids=["p1-b1"])
        self.assertEqual(plan["specs"], [])
        self.assertIn("not enabled in conservative mode", plan["skipped"][0]["reason"])

    def test_parameter_suggestions_respect_constraints(self):
        b = bank()
        q = next(x for x in b["questions"] if x["id"] == "p2-a3")
        q["constraints"].append({"text": "x below 0.16 m", "var": "x", "op": "<", "value": 0.16})
        plan = plan_mutations(b, genomes(), operators=["parameter"], question_ids=["p2-a3"], seed=0)
        for s in plan["specs"]:
            for ch in s["parameters"]["changes"]:
                if ch["symbol"] == "x":
                    self.assertLess(ch["suggested"], 0.16)

    def test_missing_genome_skipped(self):
        gs = [g for g in genomes() if g["question_id"] != "p1-a2"]
        plan = plan_mutations(bank(), gs, question_ids=["p1-a2"])
        self.assertEqual(plan["skipped"][0]["question_id"], "p1-a2")

    def test_variants_use_distinct_operators(self):
        plan = plan_variants(bank(), genomes(), "p1-b2", 5, seed=0)
        ops = [s["operator"] for s in plan["specs"]]
        self.assertEqual(len(ops), 5)
        self.assertEqual(len(set(ops)), 5)

    def test_fusion_partner_is_related(self):
        plan = plan_mutations(bank(), genomes(), mode="exploratory", operators=["fusion"], question_ids=["p1-b2"], seed=0)
        self.assertEqual(len(plan["specs"]), 1)
        partner = plan["specs"][0]["parameters"]["partner_question_id"]
        self.assertNotEqual(partner, "p1-b2")

    def test_sig_figs(self):
        self.assertEqual(significant_figures(0.15), 2)
        self.assertEqual(significant_figures(120), 2)
        self.assertEqual(significant_figures(3.20), 2)
        self.assertEqual(round_sig(0.1875, 2), 0.19)
        self.assertEqual(round_sig(1234, 2), 1200)


class TestDistanceDiversityLineage(unittest.TestCase):
    def setUp(self):
        self.q = {x["id"]: x for x in bank()["questions"]}
        self.g = {x["question_id"]: x for x in genomes()}

    def test_labels(self):
        self.assertEqual([label(x) for x in (0.0, 0.2, 0.5, 0.9)], ["none", "low", "moderate", "high"])

    def test_identical_is_near_duplicate(self):
        p = distance_profile(self.q["p1-a2"], self.g["p1-a2"], self.q["p1-a2"], self.g["p1-a2"])
        self.assertEqual(p["novelty"], "near_duplicate")
        self.assertEqual(p["conceptual_equivalence"], {"status": "unverified"})
        self.assertEqual(set(p["dimensions"]), {"surface", "concept", "reasoning", "representation", "constraint", "answer"})

    def test_duplicates_detected(self):
        items = [(self.q["p1-a2"], self.g["p1-a2"]), (copy.deepcopy(self.q["p1-a2"]) | {"id": "dup"}, self.g["p1-a2"]), (self.q["p2-a6"], self.g["p2-a6"])]
        dups = find_duplicates(items)
        self.assertEqual(len(dups), 1)
        self.assertEqual({dups[0]["a"], dups[0]["b"]}, {"p1-a2", "dup"})

    def test_select_diverse_deterministic(self):
        items = [(self.q[i], self.g[i]) for i in ("p1-a2", "p1-a3", "p1-a6", "p2-a6", "p3-a3")]
        a = select_diverse(items, 3)
        self.assertEqual(a, select_diverse(list(reversed(items)), 3))
        self.assertEqual(len(a), 3)

    def test_lineage_checks(self):
        root = {"id": "r"}
        child = {"id": "c", "lineage": {"parent_id": "r", "root_id": "r", "operator": "surface", "generation": 1}}
        grand = {"id": "gc", "lineage": {"parent_id": "c", "root_id": "r", "operator": "parameter", "generation": 2}}
        lin = build_lineage([root, child, grand])
        self.assertTrue(lin["valid"])
        self.assertEqual(lin["max_generation"], 2)
        self.assertEqual(lin["families"]["r"], ["c", "gc", "r"])
        bad = build_lineage([root, {"id": "x", "lineage": {"parent_id": "missing", "operator": "surface", "generation": 1}}])
        self.assertFalse(bad["valid"])
        wrong_gen = build_lineage([root, {"id": "y", "lineage": {"parent_id": "r", "operator": "surface", "generation": 3}}])
        self.assertTrue(any("generation" in e for e in wrong_gen["errors"]))
        cyc = build_lineage([{"id": "a", "lineage": {"parent_id": "b", "operator": "s", "generation": 1}}, {"id": "b", "lineage": {"parent_id": "a", "operator": "s", "generation": 1}}])
        self.assertTrue(any("cycle" in e for e in cyc["errors"]))


if __name__ == "__main__":
    unittest.main()
