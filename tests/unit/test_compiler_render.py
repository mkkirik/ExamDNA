import copy
import unittest

from examdna.compiler import CompilationInfeasible, compile_exam
from examdna.compiler.solver import shift_bands
from examdna.extraction.normalize import normalize_question
from examdna.reporting import answer_key_markdown, exam_html, exam_markdown, marking_guide_markdown


def item(qid, marks, topic="Forces", qtype="calculation", state="PASS", root=None, section=None):
    q = normalize_question(
        {
            "id": qid,
            "text": f"Question {qid} about {topic}. Calculate something.",
            "question_type": qtype,
            "marks": marks,
            "topic": topic,
            "section": section,
            "marking": {"final_answer": "42 N", "worked_solution": "SECRET-SOLUTION", "points": [{"description": "pt", "marks": marks}]},
            "lineage": {"parent_id": root or f"src-{qid}", "root_id": root or f"src-{qid}", "operator": "surface", "generation": 1},
            "validation": {"state": state, "summary": None, "model_assisted": False, "numeric_verified": True},
        },
        origin="generated",
    )[0]
    return q


def pool(items):
    return {"schema_version": "0.1.0", "bank_id": "pool-test", "questions": items}


class TestCompiler(unittest.TestCase):
    def setUp(self):
        self.items = [item(f"q{i}", m, topic=t) for i, (m, t) in enumerate([(1, "Waves"), (2, "Forces"), (2, "Energy"), (3, "Forces"), (3, "Waves"), (4, "Energy"), (5, "Electricity"), (6, "Forces")])]

    def test_exact_marks_and_sections(self):
        cfg = {"total_marks": 12, "sections": [{"label": "A", "marks": 5}, {"label": "B", "marks": 7}], "seed": 1}
        exam = compile_exam(pool(self.items), cfg)
        self.assertEqual(sum(q["marks"] for s in exam["sections"] for q in s["questions"]), 12)
        for s in exam["sections"]:
            self.assertEqual(sum(q["marks"] for q in s["questions"]), s["marks"])
        ids = [q["id"] for s in exam["sections"] for q in s["questions"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(exam["solver"]["exhaustive"])

    def test_reproducible_with_seed(self):
        cfg = {"total_marks": 10, "seed": 5}
        a = compile_exam(pool(copy.deepcopy(self.items)), cfg)
        b = compile_exam(pool(copy.deepcopy(self.items)), cfg)
        self.assertEqual(a, b)

    def test_required_topic_and_exclusion(self):
        exam = compile_exam(pool(self.items), {"total_marks": 8, "required_topics": ["Electricity"], "excluded_topics": ["Waves"]})
        topics = {q["question"]["topic"] for s in exam["sections"] for q in s["questions"]}
        self.assertIn("Electricity", topics)
        self.assertNotIn("Waves", topics)

    def test_review_required_excluded_unless_allowed(self):
        items = [item("r1", 5, state="REVIEW_REQUIRED"), item("p1", 3)]
        with self.assertRaises(CompilationInfeasible) as ctx:
            compile_exam(pool(items), {"total_marks": 8})
        self.assertEqual(ctx.exception.diagnosis["excluded"]["review_required"], 1)
        self.assertTrue(any("include_review_required" in s for s in ctx.exception.diagnosis["suggestions"]))
        exam = compile_exam(pool(items), {"total_marks": 8, "include_review_required": True})
        self.assertEqual(exam["properties"]["review_required_questions"], ["r1"])

    def test_failed_and_source_questions_never_used(self):
        failed = item("f1", 3, state="FAIL")
        src = normalize_question({"id": "s1", "text": "source q", "marks": 3, "validation": {"state": "PASS"}})[0]
        with self.assertRaises(CompilationInfeasible):
            compile_exam(pool([failed, src]), {"total_marks": 3})

    def test_family_limit(self):
        items = [item("a", 2, root="R"), item("b", 2, root="R"), item("c", 2, root="S")]
        with self.assertRaises(CompilationInfeasible):
            compile_exam(pool(items), {"total_marks": 6})
        exam = compile_exam(pool(items), {"total_marks": 6, "max_per_family": 2})
        self.assertEqual(exam["question_count"], 3)

    def test_infeasible_marks_diagnosis(self):
        items = [item("x", 4), item("y", 4)]
        with self.assertRaises(CompilationInfeasible) as ctx:
            compile_exam(pool(items), {"total_marks": 6})
        d = ctx.exception.diagnosis
        self.assertFalse(d["sections"][0]["target_reachable"])
        self.assertEqual(d["sections"][0]["nearest_reachable_below"], 4)
        self.assertEqual(d["sections"][0]["nearest_reachable_above"], 8)

    def test_section_sum_conflict(self):
        with self.assertRaises(CompilationInfeasible) as ctx:
            compile_exam(pool(self.items), {"total_marks": 10, "sections": [{"label": "A", "marks": 3}, {"label": "B", "marks": 3}]})
        self.assertEqual(ctx.exception.diagnosis["conflict"], "section_marks_vs_total")

    def test_invalid_config_rejected(self):
        with self.assertRaises(ValueError):
            compile_exam(pool(self.items), {"total_marks": -3})

    def test_shift_bands(self):
        self.assertEqual(shift_bands({"foundation": 0.2, "standard": 0.5, "challenging": 0.3}, 1), {"standard": 0.2, "challenging": 0.8})
        self.assertEqual(shift_bands({"standard": 1.0}, -1), {"foundation": 1.0})


class TestRender(unittest.TestCase):
    def setUp(self):
        items = [item("q1", 2), item("q2", 3, state="REVIEW_REQUIRED")]
        items[0]["text"] = "Compute <script>alert(1)</script> force."
        self.exam = compile_exam(pool(items), {"total_marks": 5, "include_review_required": True, "time_minutes": 10, "title": "T & Exam"})

    def test_student_paper_has_no_answers(self):
        for text in (exam_markdown(self.exam), exam_html(self.exam)):
            self.assertNotIn("SECRET-SOLUTION", text)
            self.assertNotIn("42 N", text)
            self.assertNotIn("REVIEW", text)
            self.assertIn("Not an official examination", text)

    def test_html_escaping_and_print_css(self):
        html = exam_html(self.exam)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("@page { size: A4", html)
        self.assertIn("T &amp; Exam", html)

    def test_answer_key_and_guide(self):
        key = answer_key_markdown(self.exam)
        self.assertIn("42 N", key)
        self.assertIn("REVIEW REQUIRED", key)
        guide = marking_guide_markdown(self.exam)
        self.assertIn("| 1 | pt |", guide)

    def test_turkish_labels(self):
        exam = dict(self.exam, language="tr")
        self.assertIn("Toplam puan", exam_markdown(exam))
        self.assertIn("Cevap Anahtarı", answer_key_markdown(exam))


if __name__ == "__main__":
    unittest.main()
