import unittest

from tests.helpers import mini_question
from examdna.extraction.normalize import normalize_question
from examdna.validation import aggregate, validate_question
from examdna.validation.checks import numbers_in
from examdna.validation.expression import ExpressionError, evaluate, names_in
from examdna.validation.units import UnitError, convert, expression_dimensions, parse_unit


def q(**kw):
    return normalize_question(mini_question(**kw))[0]


def statuses(checks):
    return {c["check"]: c["status"] for c in checks}


NUM = {"kind": "numeric", "expression": "m*a", "variables": {"m": 2.0, "a": 3.0}, "claimed_value": 6.0, "claimed_unit": "N"}


class TestExpression(unittest.TestCase):
    def test_exact_and_float(self):
        self.assertEqual(evaluate("(v**2 - u**2)/(2*a)", {"v": 12, "u": 0, "a": 3}), (24.0, True))
        self.assertEqual(evaluate("0.1 + 0.2", {}), (0.3, True))  # exact via fractions
        v, exact = evaluate("sqrt(2*g*h)", {"g": 9.8, "h": 3.2})
        self.assertFalse(exact)
        self.assertAlmostEqual(v, 7.919595949, places=6)
        self.assertEqual(evaluate("2^3", {}), (8.0, True))

    def test_rejects_unsafe_or_invalid(self):
        for expr in ("__import__('os').system('x')", "x.__class__", "open('f')", "[1,2]", "lambda: 1", "a if b else c", "10**1000", "1/0", "unknown + 1", "", "x" * 600, "f(x=1)"):
            with self.assertRaises(ExpressionError, msg=expr):
                evaluate(expr, {"x": 1, "a": 1, "b": 1, "c": 1})

    def test_names(self):
        self.assertEqual(names_in("sqrt(2*g*h) + pi"), {"g", "h"})


class TestUnits(unittest.TestCase):
    def test_parse_and_convert(self):
        self.assertEqual(parse_unit("N")[1], parse_unit("kg m/s^2")[1])
        self.assertEqual(parse_unit("J")[1], parse_unit("N m")[1])
        self.assertAlmostEqual(convert(72, "km/h", "m/s"), 20.0)
        self.assertAlmostEqual(convert(1, "kJ", "J"), 1000)
        self.assertEqual(parse_unit("ohm")[1], parse_unit("V/A")[1])
        with self.assertRaises(UnitError):
            parse_unit("furlong")

    def test_expression_dimensions(self):
        self.assertEqual(expression_dimensions("sqrt(2*g*h)", {"g": "m/s^2", "h": "m"}), parse_unit("m/s")[1])
        with self.assertRaises(UnitError):
            expression_dimensions("v + t", {"v": "m/s", "t": "s"})
        with self.assertRaises(UnitError):
            expression_dimensions("sin(x)", {"x": "m"})
        with self.assertRaises(UnitError):
            expression_dimensions("a*b", {"a": "m"})


class TestQuestionChecks(unittest.TestCase):
    def test_correct_numeric_passes(self):
        checks = validate_question(q(), NUM)
        s = statuses(checks)
        self.assertEqual(s["recompute"], "PASS")
        self.assertEqual(s["units"], "PASS")
        self.assertEqual(s["final_answer_matches"], "PASS")
        self.assertEqual(aggregate(checks), "PASS")

    def test_wrong_claim_fails(self):
        checks = validate_question(q(), dict(NUM, claimed_value=7.0))
        self.assertEqual(statuses(checks)["recompute"], "FAIL")
        self.assertEqual(aggregate(checks), "FAIL")

    def test_wrong_unit_fails(self):
        self.assertEqual(statuses(validate_question(q(), dict(NUM, claimed_unit="J")))["units"], "FAIL")

    def test_inconsistent_given_fails(self):
        self.assertEqual(statuses(validate_question(q(), dict(NUM, variables={"m": 2.5, "a": 3.0}, claimed_value=7.5)))["givens_consistent"], "FAIL")

    def test_si_converted_given_accepted(self):
        qq = q(given=[{"symbol": "v", "value": 72, "unit": "km/h"}, {"symbol": "t", "value": 10, "unit": "s"}], marking={"final_answer": "2.0 m/s²", "points": [{"description": "x", "marks": 2}]})
        checks = validate_question(qq, {"kind": "numeric", "expression": "v/t", "variables": {"v": 20, "t": 10}, "claimed_value": 2.0, "claimed_unit": "m/s^2"})
        self.assertNotIn("givens_consistent", statuses(checks))
        self.assertEqual(aggregate(checks), "PASS")

    def test_missing_information(self):
        self.assertEqual(statuses(validate_question(q(), dict(NUM, expression="m*a*k")))["missing_information"], "FAIL")

    def test_value_not_stated_is_review(self):
        checks = validate_question(q(), dict(NUM, expression="m*g", variables={"m": 2.0, "g": 9.8}, claimed_value=19.6, claimed_unit="N"))
        self.assertEqual(statuses(checks)["value_stated"], "REVIEW_REQUIRED")

    def test_domain_and_uniqueness(self):
        s = statuses(validate_question(q(), dict(NUM, domain=[{"var": "result", "max": 5}])))
        self.assertEqual(s["domain"], "FAIL")
        s = statuses(validate_question(q(), dict(NUM, answer_uniqueness="multiple")))
        self.assertEqual(s["uniqueness"], "FAIL")
        s = statuses(validate_question(q(marking={"final_answer": "6.0 N", "accept_rule": "any value", "points": [{"description": "x", "marks": 2}]}), dict(NUM, answer_uniqueness="multiple")))
        self.assertEqual(s["uniqueness"], "PASS")

    def test_marking_total_mismatch(self):
        self.assertEqual(statuses(validate_question(q(marks=3), NUM))["marking_total"], "FAIL")

    def test_contradictory_constraints(self):
        cons = [{"text": "m > 5", "var": "m", "op": ">", "value": 5}, {"text": "m < 3", "var": "m", "op": "<", "value": 3}]
        s = statuses(validate_question(q(constraints=cons), NUM))
        self.assertEqual(s["constraint_consistency"], "FAIL")
        cons2 = [{"text": "m <= 1", "var": "m", "op": "<=", "value": 1}]
        self.assertEqual(statuses(validate_question(q(constraints=cons2), NUM))["given_satisfies_constraint"], "FAIL")

    def test_figure_reference_without_figure(self):
        s = statuses(validate_question(q(text="Use the graph shown below to find the force."), NUM))
        self.assertEqual(s["figure_specified"], "REVIEW_REQUIRED")

    def test_multiple_choice(self):
        opts = [{"key": "A", "text": "6.0 N"}, {"key": "B", "text": "1.5 N"}]
        good = q(question_type="multiple_choice", marks=1, options=opts, marking={"answer_key": "A", "final_answer": "6.0 N", "points": [{"description": "A", "marks": 1}]})
        self.assertEqual(statuses(validate_question(good, NUM))["mc_key_correct"], "PASS")
        wrong = q(question_type="multiple_choice", marks=1, options=opts, marking={"answer_key": "B", "points": [{"description": "B", "marks": 1}]})
        self.assertEqual(statuses(validate_question(wrong, NUM))["mc_key_correct"], "FAIL")
        missing = q(question_type="multiple_choice", marks=1, options=opts, marking={"answer_key": "Z", "points": [{"description": "Z", "marks": 1}]})
        self.assertEqual(statuses(validate_question(missing))["mc_key"], "FAIL")
        unverified = q(question_type="multiple_choice", marks=1, options=opts, marking={"answer_key": "A", "points": [{"description": "A", "marks": 1}]})
        self.assertEqual(aggregate(validate_question(unverified)), "REVIEW_REQUIRED")

    def test_qualitative_needs_review(self):
        qq = q(question_type="short_answer", given=[], marking={"final_answer": "No resultant force", "points": [{"description": "x", "marks": 2}]})
        self.assertEqual(aggregate(validate_question(qq)), "REVIEW_REQUIRED")

    def test_numbers_in(self):
        self.assertEqual(numbers_in("(a) 10 Ω (b) 1.2 A"), [10.0, 1.2])
        self.assertIn(220000.0, numbers_in("2.2 × 10^5 J"))
        self.assertIn(18000.0, numbers_in("18 000 kg m/s"))
        self.assertIn(200000000.0, numbers_in("2.0 × 10⁸ m/s"))


if __name__ == "__main__":
    unittest.main()
