import unittest

from tests.helpers import INPUTS, mini_question
from examdna.extraction.loaders import load_source, parse_text_exam
from examdna.extraction.normalize import merge_banks, normalize_bank, normalize_question
from examdna.utilities.io import InputError


class TestNormalize(unittest.TestCase):
    def test_aliases_and_types(self):
        q, issues = normalize_question({"id": "x1", "question": "State Newton's first law.", "type": "short", "mark": "[2 marks]", "lo": "F3; F1"})
        self.assertEqual(q["text"], "State Newton's first law.")
        self.assertEqual(q["question_type"], "short_answer")
        self.assertEqual(q["marks"], 2)
        self.assertEqual(q["learning_objectives"], ["F3", "F1"])
        self.assertEqual(issues, [])

    def test_missing_marks_are_not_invented(self):
        q, _ = normalize_question({"id": "x2", "text": "Explain refraction."})
        self.assertIsNone(q["marks"])
        self.assertIn("marks", q["missing_fields"])
        self.assertNotIn("marks", q["provenance"])

    def test_marks_calculated_from_parts_are_labelled(self):
        q, issues = normalize_question({"id": "x3", "text": "Stem", "parts": [{"label": "a", "text": "p", "marks": 2}, {"label": "b", "text": "q", "marks": 3}]})
        self.assertEqual(q["marks"], 5)
        self.assertEqual(q["provenance"]["marks"], "calculated")
        self.assertTrue(any("calculated" in i for i in issues))

    def test_part_mark_mismatch_reported(self):
        _, issues = normalize_question({"id": "x4", "text": "Stem", "marks": 4, "parts": [{"label": "a", "text": "p", "marks": 2}]})
        self.assertTrue(any("part marks sum" in i for i in issues))

    def test_provenance_defaults_and_overrides(self):
        q, _ = normalize_question(dict(mini_question(), provenance={"topic": "inferred"}))
        self.assertEqual(q["provenance"]["topic"], "inferred")
        self.assertEqual(q["provenance"]["marks"], "explicit")

    def test_unknown_type_is_reported_not_guessed(self):
        q, issues = normalize_question({"id": "x5", "text": "T", "type": "riddle"})
        self.assertIsNone(q["question_type"])
        self.assertTrue(any("unknown question type" in i for i in issues))

    def test_invalid_id_replaced(self):
        q, issues = normalize_question({"id": "../etc/passwd", "text": "T"})
        self.assertNotIn("/", q["id"])
        self.assertTrue(any("invalid id" in i for i in issues))

    def test_empty_text_rejected(self):
        with self.assertRaises(InputError):
            normalize_question({"id": "x", "text": "  "})

    def test_conflicting_ids_rejected(self):
        with self.assertRaises(InputError) as ctx:
            normalize_bank([{"id": "a", "text": "one"}, {"id": "a", "text": "two"}])
        self.assertIn("conflicting", str(ctx.exception))

    def test_merge_rejects_cross_bank_conflict(self):
        b1 = normalize_bank([{"id": "a", "text": "one"}])
        b2 = normalize_bank([{"id": "a", "text": "two"}])
        with self.assertRaises(InputError):
            merge_banks([b1, b2])

    def test_bank_shape_validation(self):
        with self.assertRaises(InputError):
            normalize_bank({"items": []})
        with self.assertRaises(InputError):
            normalize_bank(["not an object"])


class TestLoaders(unittest.TestCase):
    def test_text_parser_on_synthetic_paper(self):
        bank = load_source(INPUTS / "paper1.md", subject="Physics")
        qs = bank["questions"]
        self.assertEqual(len(qs), 9)
        self.assertEqual([q["section"] for q in qs].count("A"), 6)
        self.assertEqual(sum(q["marks"] for q in qs), 30)
        b1 = next(q for q in qs if q["section"] == "B")
        self.assertEqual([p["marks"] for p in b1["parts"]], [3, 2, 2])
        self.assertTrue(all(q["source"]["origin"] == "agent_extracted" for q in qs))

    def test_text_parser_basic(self):
        raw = parse_text_exam("Section A\n1. What is 2+2? [1 mark]\n2. Explain.\n(a) part one [2]\n(b) part two [3]\n", "t.md")
        self.assertEqual(len(raw["questions"]), 2)
        self.assertEqual(raw["questions"][1]["parts"][1]["marks"], 3)

    def test_csv_loader(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bank.csv"
            p.write_text("id,text,marks,topic,learning_objectives\nc1,Define power.,1,Energy,E2;U1\n", encoding="utf-8")
            bank = load_source(p)
            self.assertEqual(bank["questions"][0]["learning_objectives"], ["E2", "U1"])
            p.write_text("id,question\nc1,missing text column\n", encoding="utf-8")
            with self.assertRaises(InputError):
                load_source(p)

    def test_structured_bank_loads_cleanly(self):
        bank = load_source(INPUTS / "physics_bank.json")
        self.assertEqual(len(bank["questions"]), 27)
        self.assertEqual(bank["normalization_report"]["issues"], [])


if __name__ == "__main__":
    unittest.main()
