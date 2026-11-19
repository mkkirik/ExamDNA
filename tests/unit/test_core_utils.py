import unittest

from tests.helpers import ROOT  # noqa: F401  (sets sys.path)
from examdna.models.schema import validate
from examdna.utilities.ids import is_valid_id, seed_for, slugify, stable_id
from examdna.utilities.stats import (
    evidence_level,
    jaccard,
    largest_remainder,
    normalized_edit_similarity,
    proportions,
    summary,
    surface_similarity,
    total_variation,
)


class TestIds(unittest.TestCase):
    def test_stable_id_is_deterministic_and_content_sensitive(self):
        self.assertEqual(stable_id("spec", 1, "a"), stable_id("spec", 1, "a"))
        self.assertNotEqual(stable_id("spec", 1, "a"), stable_id("spec", 2, "a"))
        self.assertTrue(is_valid_id(stable_id("spec", {"x": [1, 2]})))

    def test_id_validation(self):
        self.assertTrue(is_valid_id("p1-a2"))
        for bad in ("", "../x", "a b", "-lead", "a/b", None, 3, "x" * 200):
            self.assertFalse(is_valid_id(bad), bad)

    def test_slugify_and_seed(self):
        self.assertEqual(slugify("Fizik Sınavı 1!"), "fizik-sinavi-1")
        self.assertEqual(seed_for("a", 1), seed_for("a", 1))


class TestStats(unittest.TestCase):
    def test_total_variation(self):
        self.assertEqual(total_variation({"a": 1}, {"a": 5}), 0.0)
        self.assertEqual(total_variation({"a": 1}, {"b": 1}), 1.0)
        self.assertAlmostEqual(total_variation({"a": 3, "b": 1}, {"a": 1, "b": 1}), 0.25)

    def test_summary_and_proportions(self):
        s = summary([30, 30, 32])
        self.assertEqual((s["n"], s["median"], s["min"], s["max"]), (3, 30.0, 30, 32))
        self.assertEqual(proportions({"a": 1, "b": 3}), {"a": 0.25, "b": 0.75})
        self.assertEqual(summary([])["mean"], None)

    def test_largest_remainder_preserves_total(self):
        alloc = largest_remainder(30, {"A": 0.3478, "B": 0.6522})
        self.assertEqual(sum(alloc.values()), 30)
        self.assertEqual(alloc, {"A": 10, "B": 20})
        self.assertEqual(sum(largest_remainder(7, {"x": 1, "y": 1, "z": 1}).values()), 7)

    def test_similarity_measures(self):
        self.assertEqual(jaccard([], []), 1.0)
        self.assertAlmostEqual(jaccard([1, 2], [2, 3]), 1 / 3)
        self.assertEqual(normalized_edit_similarity(["a", "b"], ["a", "b"]), 1.0)
        self.assertEqual(normalized_edit_similarity(["a", "b"], ["c", "d"]), 0.0)
        base = "A spring with spring constant 40 N/m is extended by 0.15 m. Calculate the force applied to the spring."
        swapped = base.replace("0.15", "0.19")
        self.assertGreater(surface_similarity(base, swapped), 0.9)
        self.assertLess(surface_similarity(base, "Find the potential difference across a resistor."), 0.3)

    def test_evidence_level(self):
        self.assertEqual([evidence_level(n) for n in (1, 2, 3, 5, 12)], ["insufficient", "limited", "limited", "moderate", "substantial"])


class TestSchemaValidator(unittest.TestCase):
    SCHEMA = {
        "type": "object",
        "required": ["a"],
        "additionalProperties": False,
        "definitions": {"pos": {"type": "integer", "minimum": 1}},
        "properties": {
            "a": {"$ref": "#/definitions/pos"},
            "b": {"enum": ["x", "y", None]},
            "c": {"type": "array", "items": {"type": "string", "pattern": "^[a-z]+$"}, "maxItems": 2, "uniqueItems": True},
            "d": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
        },
    }

    def test_valid(self):
        self.assertEqual(validate({"a": 2, "b": None, "c": ["ab"], "d": 3}, self.SCHEMA), [])

    def test_errors(self):
        errs = validate({"b": "z", "c": ["A", "b", "c"], "d": 1.5, "e": 1}, self.SCHEMA)
        joined = " | ".join(errs)
        for fragment in ("missing required field 'a'", "not one of", "does not match pattern", "more than 2", "any allowed form", "unexpected field 'e'"):
            self.assertIn(fragment, joined)

    def test_bool_is_not_integer(self):
        self.assertTrue(validate({"a": True}, self.SCHEMA))

    def test_all_schemas_load(self):
        from examdna.models.schema import SCHEMA_NAMES, load_schema

        for name in SCHEMA_NAMES:
            self.assertIn("type", load_schema(name))


if __name__ == "__main__":
    unittest.main()
