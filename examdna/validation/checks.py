"""Individual validation checks.

Every check returns a dict::

    {"stage": ..., "check": ..., "status": PASS|FAIL|REVIEW_REQUIRED|NOT_VERIFIED|INFO,
     "method": "deterministic"|"model_assisted", "message": ...}

``INFO`` findings are reported but do not change the aggregate state.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional

from ..models.constants import FAIL, NOT_VERIFIED, PASS, REVIEW_REQUIRED
from .expression import ExpressionError, evaluate, names_in
from .units import UnitError, convert, expression_dimensions, parse_unit

INFO = "INFO"
DEFAULT_RELATIVE_TOLERANCE = 0.01
_FIGURE_WORDS = re.compile(r"\b(diagram|figure|graph shown|shown below|shown above|the graph|the table|table below|circuit shown)\b", re.IGNORECASE)
_VAGUE = re.compile(r"\b(etc\.?|and so on|roughly|a few|some amount|a lot of|large amount|suitable value|reasonable value)\b", re.IGNORECASE)


_NUMBER = re.compile(r"[-−]?\d+(?:[.,]\d+)?(?:\s*[×x*]\s*10\^?\s*[-−]?\d+|[eE][-−]?\d+)?")


def _parse_number(raw: str) -> Optional[float]:
    raw = raw.replace("−", "-").replace(",", ".")
    sci = re.match(r"\s*([-]?\d+(?:\.\d+)?)\s*[×x*]\s*10\^?\s*([-]?\d+)", raw)
    try:
        if sci:
            return float(f"{sci.group(1)}e{int(sci.group(2))}")  # avoids 2.2 * 10**5 float drift
        return float(raw)
    except ValueError:
        return None


def numbers_in(text: str) -> List[float]:
    """All numbers in a string, understanding ``3.2 × 10^4``, ``3.2e4`` and ``18 000``."""
    if not text:
        return []
    text = re.sub(r"(?<=\d) (?=\d{3}\b)", "", text)  # thousands separator "18 000"
    text = text.replace("⁰", "0").replace("¹", "1").replace("²", "2").replace("³", "3").replace("⁴", "4").replace("⁵", "5").replace("⁶", "6").replace("⁷", "7").replace("⁸", "8").replace("⁹", "9").replace("⁻", "-")
    out = []
    for m in _NUMBER.finditer(text):
        v = _parse_number(m.group(0))
        if v is not None:
            out.append(v)
    return out


def first_number(text: str) -> Optional[float]:
    nums = numbers_in(text)
    return nums[0] if nums else None


def chk(stage: str, check: str, status: str, message: str, method: str = "deterministic") -> Dict[str, Any]:
    return {"stage": stage, "check": check, "status": status, "method": method, "message": message}


# ---------------------------------------------------------------- structure
def structural_checks(q: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    if q.get("marks") is None:
        out.append(chk("structural", "marks_present", REVIEW_REQUIRED, "question has no mark allocation"))
    else:
        out.append(chk("structural", "marks_present", PASS, f"{q['marks']} marks"))
    parts = q.get("parts") or []
    if parts:
        pm = [p.get("marks") for p in parts]
        if None in pm:
            out.append(chk("structural", "part_marks", REVIEW_REQUIRED, "some parts have no marks"))
        elif q.get("marks") is not None and sum(pm) != q["marks"]:
            out.append(chk("structural", "part_marks", FAIL, f"part marks sum to {sum(pm)} but question is worth {q['marks']}"))
        else:
            out.append(chk("structural", "part_marks", PASS, "part marks consistent"))
        labels = [p["label"] for p in parts]
        if len(labels) != len(set(labels)):
            out.append(chk("structural", "part_labels", FAIL, "duplicate part labels"))
    marking = q.get("marking") or {}
    points = marking.get("points") or []
    if points and q.get("marks") is not None:
        total = sum(p["marks"] for p in points)
        if total != q["marks"]:
            out.append(chk("answer_marking", "marking_total", FAIL, f"marking points total {total} but question is worth {q['marks']}"))
        else:
            out.append(chk("answer_marking", "marking_total", PASS, "marking points match marks"))
        if parts:
            by_part = defaultdict(int)
            for p in points:
                if p.get("part"):
                    by_part[p["part"]] += p["marks"]
            for part in parts:
                if part["label"] in by_part and part.get("marks") is not None and by_part[part["label"]] != part["marks"]:
                    out.append(
                        chk("answer_marking", "marking_by_part", FAIL, f"part ({part['label']}) marking points total {by_part[part['label']]} but part is worth {part['marks']}")
                    )
    elif not marking or not (marking.get("final_answer") or marking.get("answer_key") or points):
        out.append(chk("answer_marking", "marking_present", REVIEW_REQUIRED, "no answer or marking information"))
    if q.get("question_type") == "multiple_choice":
        opts = q.get("options") or []
        keys = [o["key"] for o in opts]
        if len(opts) < 2:
            out.append(chk("structural", "mc_options", FAIL, "multiple-choice item needs at least two options"))
        elif len(keys) != len(set(keys)):
            out.append(chk("structural", "mc_options", FAIL, "duplicate option keys"))
        elif len({o["text"].strip().lower() for o in opts}) != len(opts):
            out.append(chk("ambiguity", "mc_duplicate_options", FAIL, "two options have identical text"))
        else:
            out.append(chk("structural", "mc_options", PASS, f"{len(opts)} options"))
        key = marking.get("answer_key")
        if key is None:
            out.append(chk("answer_marking", "mc_key", REVIEW_REQUIRED, "no answer key"))
        elif key not in keys:
            out.append(chk("answer_marking", "mc_key", FAIL, f"answer key {key!r} is not one of the options"))
        else:
            out.append(chk("answer_marking", "mc_key", PASS, f"answer key {key}"))
    text = " ".join([q["text"], *[p["text"] for p in parts]])
    if _FIGURE_WORDS.search(text) and not (q.get("diagram_description") or q.get("table")):
        out.append(chk("ambiguity", "figure_specified", REVIEW_REQUIRED, "text refers to a figure/graph/table that is not supplied"))
    vague = sorted({m.group(0).lower() for m in _VAGUE.finditer(text)})
    if vague:
        out.append(chk("ambiguity", "vague_terms", INFO, f"vague wording: {', '.join(vague)}"))
    if q.get("security_flags"):
        out.append(chk("security", "instruction_like_text", REVIEW_REQUIRED, f"instruction-like text in question: {', '.join(q['security_flags'])}"))
    return out


# ---------------------------------------------------------------- constraints
_OPS = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b, "==": lambda a, b: a == b, "!=": lambda a, b: a != b}


def constraint_checks(q: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    numeric = [c for c in q.get("constraints") or [] if c.get("var") and c.get("op") in _OPS and isinstance(c.get("value"), (int, float))]
    if not numeric:
        return out
    by_var = defaultdict(list)
    for c in numeric:
        by_var[c["var"]].append(c)
    for var, cs in sorted(by_var.items()):
        lo, lo_incl, hi, hi_incl = -math.inf, True, math.inf, True
        eq = set()
        for c in cs:
            v = c["value"]
            if c["op"] in (">", ">="):
                if v > lo or (v == lo and c["op"] == ">"):
                    lo, lo_incl = v, c["op"] == ">="
            elif c["op"] in ("<", "<="):
                if v < hi or (v == hi and c["op"] == "<"):
                    hi, hi_incl = v, c["op"] == "<="
            elif c["op"] == "==":
                eq.add(v)
        empty = lo > hi or (lo == hi and not (lo_incl and hi_incl)) or len(eq) > 1
        if eq and not empty:
            e = next(iter(eq))
            empty = not ((e > lo or (e == lo and lo_incl)) and (e < hi or (e == hi and hi_incl)))
        if empty:
            out.append(chk("ambiguity", "constraint_consistency", FAIL, f"constraints on '{var}' contradict each other ({'; '.join(c['text'] for c in cs)})"))
        else:
            out.append(chk("ambiguity", "constraint_consistency", PASS, f"constraints on '{var}' are satisfiable"))
    givens = {g["symbol"]: g.get("value") for g in q.get("given") or [] if isinstance(g.get("value"), (int, float))}
    for c in numeric:
        if c["var"] in givens and not _OPS[c["op"]](givens[c["var"]], c["value"]):
            out.append(chk("ambiguity", "given_satisfies_constraint", FAIL, f"given {c['var']} = {givens[c['var']]} violates constraint '{c['text']}'"))
    return out


# ---------------------------------------------------------------- numeric
def _close(a: float, b: float, rel: float) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-12)


def numeric_checks(q: Dict[str, Any], verification: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not verification or verification.get("kind") != "numeric":
        return out
    expr = verification.get("expression")
    variables = dict(verification.get("variables") or {})
    if not expr:
        return [chk("numeric", "expression_present", FAIL, "numeric verification declared without an expression")]
    used = names_in(expr)
    undefined = sorted(used - set(variables))
    if undefined:
        out.append(chk("numeric", "missing_information", FAIL, f"expression uses undefined quantities: {', '.join(undefined)}"))
        return out

    givens = {g["symbol"]: g for g in q.get("given") or []}
    for var, val in sorted(variables.items()):
        g = givens.get(var)
        if g is None:
            if var in used:
                out.append(chk("ambiguity", "value_stated", REVIEW_REQUIRED, f"'{var}' is used in the solution but not stated in the question's given data"))
            continue
        if not isinstance(g.get("value"), (int, float)):
            continue
        gv = g["value"]
        same = _close(val, gv, 1e-9)
        if not same and g.get("unit"):
            try:
                si_scale, _ = parse_unit(g["unit"])
                same = _close(val, gv * si_scale, 1e-9)
            except UnitError:
                pass
        if not same:
            out.append(chk("numeric", "givens_consistent", FAIL, f"verification uses {var} = {val} but the question gives {gv} {g.get('unit') or ''}".strip()))
    unused = sorted(s for s, g in givens.items() if s not in used and g.get("role") not in ("distractor", "constant") and isinstance(g.get("value"), (int, float)))
    if unused:
        out.append(chk("ambiguity", "unused_given", INFO, f"given value(s) not used by the final expression: {', '.join(unused)}"))

    try:
        value, exact = evaluate(expr, variables)
    except ExpressionError as exc:
        out.append(chk("numeric", "recompute", FAIL, f"expression could not be evaluated: {exc}"))
        return out
    mode = "exact rational arithmetic" if exact else "floating point"
    rel = verification.get("relative_tolerance") or DEFAULT_RELATIVE_TOLERANCE
    claimed = verification.get("claimed_value")
    if claimed is None:
        out.append(chk("numeric", "recompute", REVIEW_REQUIRED, f"recomputed {value:.6g} ({mode}) but no claimed value to compare"))
    elif _close(value, claimed, rel):
        out.append(chk("numeric", "recompute", PASS, f"claimed {claimed:g} matches recomputed {value:.6g} ({mode}, tolerance {rel:g})"))
    else:
        out.append(chk("numeric", "recompute", FAIL, f"claimed {claimed:g} but recomputed {value:.6g} ({mode})"))

    final = ((q.get("marking") or {}).get("final_answer")) or ""
    stated = numbers_in(final)
    if stated and claimed is not None:
        tol = max(rel, 0.02)
        if any(_close(s, claimed, tol) for s in stated):
            out.append(chk("answer_marking", "final_answer_matches", PASS, "final answer text contains the verified value"))
        else:
            shown = ", ".join(f"{s:g}" for s in stated[:4])
            out.append(chk("answer_marking", "final_answer_matches", FAIL, f"marking final answer states {shown} but verification claims {claimed:g}"))

    unit = verification.get("claimed_unit")
    var_units = {s: g.get("unit") for s, g in givens.items()}
    for s in variables:
        var_units.setdefault(s, None)
    if unit:
        try:
            dims = expression_dimensions(expr, var_units)
            if parse_unit(unit)[1] == dims:
                out.append(chk("numeric", "units", PASS, f"dimensions of the expression match '{unit}'"))
            else:
                out.append(chk("numeric", "units", FAIL, f"expression dimensions do not match claimed unit '{unit}'"))
        except UnitError as exc:
            out.append(chk("numeric", "units", NOT_VERIFIED, f"unit check not possible: {exc}"))
    else:
        out.append(chk("numeric", "units", NOT_VERIFIED, "no claimed unit"))

    for d in verification.get("domain") or []:
        target = d["var"]
        v = value if target == "result" else variables.get(target)
        if v is None:
            out.append(chk("numeric", "domain", NOT_VERIFIED, f"domain variable '{target}' not found"))
            continue
        excl = d.get("exclusive", False)
        lo_bad = d.get("min") is not None and (v < d["min"] or (excl and v == d["min"]))
        hi_bad = d.get("max") is not None and (v > d["max"] or (excl and v == d["max"]))
        if lo_bad or hi_bad:
            out.append(chk("numeric", "domain", FAIL, f"{target} = {v:.6g} is outside its allowed domain [{d.get('min')}, {d.get('max')}]"))
        else:
            out.append(chk("numeric", "domain", PASS, f"{target} within domain"))

    uniq = verification.get("answer_uniqueness", "unique")
    accept = (q.get("marking") or {}).get("accept_rule")
    if uniq == "multiple" and not accept:
        out.append(chk("ambiguity", "uniqueness", FAIL, "several answers are valid but no marking accept_rule is defined"))
    elif uniq == "multiple":
        out.append(chk("ambiguity", "uniqueness", PASS, "multiple answers covered by accept_rule"))
    elif uniq == "unknown":
        out.append(chk("ambiguity", "uniqueness", REVIEW_REQUIRED, "answer uniqueness not established"))
    return out


def answer_checks(
    q: Dict[str, Any], verification: Optional[Dict[str, Any]], judgements: Optional[Dict[str, bool]] = None
) -> List[Dict[str, Any]]:
    """Decide how the answer was (or was not) verified."""
    judgements = judgements or {}
    kind = (verification or {}).get("kind")
    marking = q.get("marking") or {}
    if q.get("question_type") == "multiple_choice":
        key = marking.get("answer_key")
        opts = {o["key"]: o["text"] for o in q.get("options") or []}
        if kind == "numeric" and key in opts and verification.get("claimed_value") is not None:
            shown = first_number(opts[key])
            if shown is not None and _close(shown, verification["claimed_value"], 0.02):
                return [chk("answer_marking", "mc_key_correct", PASS, f"keyed option {key} matches the verified value")]
            return [chk("answer_marking", "mc_key_correct", FAIL, f"keyed option {key} does not show the verified value")]
        if "answer_correct" in judgements:
            status = PASS if judgements["answer_correct"] else FAIL
            return [chk("answer_marking", "mc_key_correct", status, "agent judgement on answer key", method="model_assisted")]
        if q.get("review_status") == "human_reviewed":
            return [chk("answer_marking", "mc_key_correct", PASS, "answer key accepted by human review", method="human")]
        return [chk("answer_marking", "mc_key_correct", REVIEW_REQUIRED, "correctness of the answer key not verified")]
    if kind == "numeric":
        return []  # covered by numeric_checks
    if q.get("review_status") == "human_reviewed":
        return [chk("answer_marking", "answer_verified", PASS, "answer accepted by human review", method="human")]
    return [chk("answer_marking", "answer_verified", REVIEW_REQUIRED, "qualitative answer: needs human review (no deterministic verification available)")]
