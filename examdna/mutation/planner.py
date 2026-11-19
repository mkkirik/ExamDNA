"""Deterministic mutation planning (Stage A of two-stage generation).

The planner chooses operators and concrete parameters; it never writes
question text. Given the same bank, genomes, options and seed it produces the
same plan, byte for byte.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from .. import SCHEMA_VERSION
from ..fingerprint.difficulty import difficulty_points, features_from_genome
from ..genome.graph import analyze_reasoning_graph
from ..models.constants import MUTATION_MODES, REPRESENTATION_TRANSFORMS
from ..models.schema import validate
from ..utilities.ids import seed_for, stable_id
from .operators import REGISTRY, MutationOperator, _numeric_givens, get_operator

CONTEXT_LIBRARY = [
    "sports and athletics",
    "road and rail transport",
    "space flight",
    "medical devices",
    "renewable energy",
    "construction and engineering",
    "household appliances",
    "amusement-park rides",
    "weather and environment",
    "music and acoustics",
    "agriculture",
    "robotics",
]
PARAMETER_FACTORS = [0.5, 0.75, 1.25, 1.5, 2.0]
_OPS = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def significant_figures(value: float) -> int:
    if value == 0:
        return 1
    text = f"{abs(value):.10g}"
    mantissa = text.split("e")[0]
    digits = mantissa.replace(".", "").lstrip("0")
    if "." not in mantissa:
        digits = digits.rstrip("0") or "1"
    return max(len(digits), 1)


def round_sig(value: float, sig: int) -> float:
    if value == 0:
        return 0.0
    rounded = round(value, sig - int(math.floor(math.log10(abs(value)))) - 1)
    return int(rounded) if float(rounded).is_integer() and abs(rounded) >= 1 else rounded


def _satisfies(question: Dict[str, Any], symbol: str, value: float) -> bool:
    for c in question.get("constraints") or []:
        if c.get("var") == symbol and c.get("op") in _OPS and isinstance(c.get("value"), (int, float)):
            if not _OPS[c["op"]](value, c["value"]):
                return False
    return True


def _params_surface(q, g, rng, ctx):
    style = rng.choice(["restate the scenario with different named objects", "reorder the information and rephrase every sentence", "write a concise technical version"])
    return {"style": style}, [f"Rewrite the question using this style: {style}. Keep every given value, unit and the required output unchanged."]


def _params_parameter(q, g, rng, ctx):
    numeric = _numeric_givens(q)
    k = min(len(numeric), rng.choice([1, 2]))
    chosen = sorted(rng.sample(range(len(numeric)), k))
    changes = []
    for idx in chosen:
        given = numeric[idx]
        old = given["value"]
        factors = PARAMETER_FACTORS[:]
        rng.shuffle(factors)
        new = None
        for f in factors:
            candidate = round_sig(old * f, max(significant_figures(old), 2))
            if candidate != old and (old <= 0 or candidate > 0) and _satisfies(q, given["symbol"], candidate):
                new = candidate
                break
        if new is None:
            continue
        changes.append({"symbol": given["symbol"], "old": old, "suggested": new, "unit": given.get("unit")})
    instructions = [
        "Replace the listed given values (suggested values may be adjusted to keep the scenario realistic).",
        "Recompute the answer and the worked solution from the new values; supply verification.expression and variables.",
    ]
    return {"changes": changes}, instructions


def _params_representation(q, g, rng, ctx):
    current = (g.get("representation") or {}).get("input") or ["verbal"]
    source = next((r for r in current if r != "verbal"), current[0])
    options = [r for r in REPRESENTATION_TRANSFORMS.get(source, ["table"]) if r not in current] or ["table"]
    target = rng.choice(options)
    return {"from": source, "to": target}, [
        f"Present the information currently given as '{source}' as a '{target}' instead.",
        "Every value needed to solve the problem must be recoverable from the new representation.",
        "Graphs must be described precisely in text or as a data table so they can be printed and checked.",
    ]


def _params_constraint(q, g, rng, ctx):
    explicit = (g.get("constraints") or {}).get("explicit") or []
    action = rng.choice(["modify", "add"]) if explicit else "add"
    params: Dict[str, Any] = {"action": action}
    if action == "modify":
        params["target_constraint"] = rng.choice(explicit)
    instructions = [
        f"{'Modify the constraint: ' + params['target_constraint'] if action == 'modify' else 'Add one new, physically justified constraint that affects the solution'}.",
        "Encode numeric conditions in question.constraints with var/op/value so they can be checked.",
        "Confirm the question remains solvable and all givens satisfy every constraint.",
    ]
    return params, instructions


def _params_reverse(q, g, rng, ctx):
    numeric = _numeric_givens(q)
    target = rng.choice(numeric)
    return {"new_unknown": target["symbol"], "new_unknown_description": target.get("description"), "original_output": q.get("required_output")}, [
        f"Make '{target['symbol']}' ({target.get('description') or 'given quantity'}) the unknown.",
        "Give the original required output as data.",
        "State verification.answer_uniqueness. If several answers are valid, set marking.accept_rule or the candidate will be rejected.",
    ]


def _params_context(q, g, rng, ctx):
    current = (g.get("representation") or {}).get("context")
    options = [c for c in CONTEXT_LIBRARY if c != current]
    target = rng.choice(options)
    return {"from_context": current, "to_context": target}, [
        f"Move the scenario into the context: {target}.",
        "Keep the same physics/mathematics model and reasoning steps; adjust values only to stay realistic.",
        "Set genome.representation.context to the new context.",
    ]


def _params_difficulty(q, g, rng, ctx):
    direction = ctx.get("difficulty_direction", "up")
    steps = (g.get("reasoning") or {}).get("steps") or []
    if direction == "up":
        adjustment = rng.choice(["add_reasoning_stage", "add_constraint", "require_interpretation", "add_representation"])
    else:
        adjustment = rng.choice(["remove_nonessential_stage", "provide_intermediate_result"]) if len(steps) >= 3 else "provide_intermediate_result"
    current = difficulty_points(features_from_genome(g))
    return {"direction": direction, "adjustment": adjustment, "current_points": current, "minimum_point_change": 2}, [
        f"Make the question {'harder' if direction == 'up' else 'easier'} by: {adjustment.replace('_', ' ')}.",
        "Update the genome's reasoning steps/constraints so the change is visible structurally.",
        "Adjust marks and marking points to match the new number of stages.",
    ]


def _params_fusion(q, g, rng, ctx):
    partner = ctx.get("partner")
    pk = partner["knowledge"]
    return {"partner_question_id": partner["question_id"], "partner_concept": pk.get("primary_concept")}, [
        f"Combine the parent's objective with '{pk.get('primary_concept')}' (from {partner['question_id']}) so that both are needed.",
        "Include both concepts in genome.knowledge (primary + secondary) and keep the parent's learning objectives.",
    ]


def _params_path(q, g, rng, ctx):
    seq = analyze_reasoning_graph(g.get("reasoning") or {})["type_sequence"]
    return {"parent_step_types": seq}, [
        "Design the question so that it is best solved by a different valid method from the parent's.",
        f"The candidate's reasoning step-type sequence must differ from: {' > '.join(seq)}.",
    ]


PARAM_BUILDERS = {
    "surface": _params_surface,
    "parameter": _params_parameter,
    "representation": _params_representation,
    "constraint": _params_constraint,
    "reverse": _params_reverse,
    "context_transfer": _params_context,
    "difficulty": _params_difficulty,
    "fusion": _params_fusion,
    "reasoning_path": _params_path,
}


def find_fusion_partner(genome: Dict[str, Any], genomes: Sequence[Dict[str, Any]], rng: random.Random) -> Optional[Dict[str, Any]]:
    k = genome.get("knowledge") or {}
    primary = (k.get("primary_concept") or "").lower()
    related = {c.lower() for c in (k.get("prerequisites") or []) + (k.get("secondary_concepts") or [])}
    eligible = []
    for other in genomes:
        ok_ = other.get("knowledge") or {}
        other_primary = (ok_.get("primary_concept") or "").lower()
        if not other_primary or other_primary == primary or other["question_id"] == genome["question_id"]:
            continue
        other_related = {c.lower() for c in (ok_.get("prerequisites") or []) + (ok_.get("secondary_concepts") or [])}
        same_topic = k.get("topic") and k.get("topic") == ok_.get("topic")
        linked = other_primary in related or primary in other_related
        if same_topic or linked:
            eligible.append(other)
    if not eligible:
        return None
    eligible.sort(key=lambda x: x["question_id"])
    return rng.choice(eligible)


def required_judgements(op: MutationOperator) -> List[str]:
    """Semantic properties the agent must explicitly judge in the candidate.

    ``target_skill`` is always required: no deterministic check can confirm
    that the same skill is assessed. ``context`` is required when it is
    preserved or must change, because it is only checkable when both genomes
    record a context string.
    """
    names = ["target_skill"]
    if "context" in op.preserve or "context" in op.must_change:
        names.append("context")
    if op.id == "fusion":
        names.append("both_concepts_required")
    return names


def _generation_of(question: Dict[str, Any]) -> int:
    lineage = question.get("lineage") or {}
    return int(lineage.get("generation", 0)) + 1


def build_spec(
    op: MutationOperator,
    question: Dict[str, Any],
    genome: Dict[str, Any],
    *,
    mode: str,
    seed: int,
    index: int,
    ctx: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    rng = random.Random(seed_for(seed, question["id"], op.id, index))
    if op.id == "fusion":
        partner = find_fusion_partner(genome, ctx.get("all_genomes", []), rng)
        if partner is None:
            return None
        ctx = {**ctx, "partner": partner}
    params, op_instructions = PARAM_BUILDERS[op.id](question, genome, rng, ctx)
    if op.id == "parameter" and not params["changes"]:
        return None
    spec = {
        "spec_id": stable_id("spec", seed, question["id"], op.id, index),
        "parent_id": question["id"],
        "parent_genome_id": genome["genome_id"],
        "operator": op.id,
        "operator_name": op.name,
        "mode": mode,
        "generation": _generation_of(question),
        "parameters": params,
        "preserve": list(op.preserve),
        "may_change": list(op.may_change),
        "must_change": list(op.must_change),
        "invariants": list(op.invariants),
        "required_judgements": required_judgements(op),
        "instructions": op_instructions
        + [
            f"Preserve: {', '.join(op.preserve)}.",
            f"Must change: {', '.join(op.must_change)}.",
            "Write an original question; do not copy sentences from the parent or any source paper.",
            "Return one JSON object matching candidate.schema.json (question + genome + verification + invariant_judgements).",
        ],
        "expected_difficulty_effect": op.expected_difficulty_effect,
        "validation_checks": list(op.validation_checks),
        "known_failure_modes": list(op.failure_modes),
        "output_contract": "candidate.schema.json",
    }
    errors = validate(spec, "mutation_spec")
    if errors:  # pragma: no cover - developer error guard
        raise ValueError("internal error: spec failed schema: " + "; ".join(errors))
    return spec


def plan_mutations(
    bank: Dict[str, Any],
    genomes: Sequence[Dict[str, Any]],
    *,
    question_ids: Optional[Sequence[str]] = None,
    operators: Optional[Sequence[str]] = None,
    mode: str = "balanced",
    per_question: int = 2,
    seed: int = 0,
    difficulty_direction: str = "up",
    max_specs: int = 500,
) -> Dict[str, Any]:
    if mode not in MUTATION_MODES:
        raise ValueError(f"mode must be one of {MUTATION_MODES}")
    if difficulty_direction not in ("up", "down"):
        raise ValueError("difficulty_direction must be 'up' or 'down'")
    if per_question < 1 or per_question > 20:
        raise ValueError("per_question must be between 1 and 20")
    requested_ops = [get_operator(o) for o in operators] if operators else None
    q_by_id = {q["id"]: q for q in bank["questions"]}
    g_by_q = {g["question_id"]: g for g in genomes}
    targets = list(question_ids) if question_ids else [q["id"] for q in bank["questions"]]
    missing = [t for t in targets if t not in q_by_id]
    if missing:
        raise ValueError(f"unknown question ids: {', '.join(missing)}")

    usage: Counter = Counter()
    specs: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    ctx_base = {"all_genomes": list(genomes), "difficulty_direction": difficulty_direction}
    for qid in targets:
        q = q_by_id[qid]
        g = g_by_q.get(qid)
        if g is None:
            skipped.append({"question_id": qid, "reason": "no genome; build and annotate a genome first"})
            continue
        if g["validation"]["structural_completeness"] == "minimal":
            skipped.append({"question_id": qid, "reason": "genome is minimal (needs primary concept and reasoning steps)"})
            continue
        pool = requested_ops or list(REGISTRY.values())
        applicable = []
        for op in pool:
            if mode not in op.modes:
                if requested_ops:
                    skipped.append({"question_id": qid, "operator": op.id, "reason": f"operator not enabled in {mode} mode"})
                continue
            ok, why = op.is_applicable(q, g)
            if ok:
                applicable.append(op)
            elif requested_ops:
                skipped.append({"question_id": qid, "operator": op.id, "reason": why})
        rng = random.Random(seed_for(seed, qid, "order"))
        keyed = sorted(applicable, key=lambda op: (usage[op.id], rng.random()))
        made = 0
        for op in keyed:
            if made >= per_question or len(specs) >= max_specs:
                break
            spec = build_spec(op, q, g, mode=mode, seed=seed, index=0, ctx=ctx_base)
            if spec is None:
                skipped.append({"question_id": qid, "operator": op.id, "reason": "no valid parameters (e.g. no fusion partner)"})
                continue
            specs.append(spec)
            usage[op.id] += 1
            made += 1
        if made == 0 and not any(s.get("question_id") == qid for s in skipped):
            skipped.append({"question_id": qid, "reason": "no applicable operator in this mode"})

    plan = {
        "schema_version": SCHEMA_VERSION,
        "plan_id": stable_id("plan", seed, mode, [s["spec_id"] for s in specs]),
        "seed": seed,
        "mode": mode,
        "specs": specs,
        "skipped": skipped,
        "notes": [
            "Specs are deterministic. Candidate text is written by the agent and is not reproducible in the same way.",
            f"Operator usage: {dict(sorted(usage.items()))}",
        ],
    }
    errors = validate(plan, "mutation_plan")
    if errors:  # pragma: no cover
        raise ValueError("internal error: plan failed schema: " + "; ".join(errors))
    return plan


def plan_variants(
    bank: Dict[str, Any],
    genomes: Sequence[Dict[str, Any]],
    question_id: str,
    count: int,
    *,
    mode: str = "exploratory",
    seed: int = 0,
    difficulty_direction: str = "up",
) -> Dict[str, Any]:
    """Plan ``count`` structurally different variants of one question.

    Operators are taken in decreasing structural rank so the variants differ
    in structure, not only in wording. If there are fewer applicable
    operators than requested, operators are reused with new parameters and a
    note says so.
    """
    q = next((x for x in bank["questions"] if x["id"] == question_id), None)
    if q is None:
        raise ValueError(f"unknown question id {question_id}")
    g = next((x for x in genomes if x["question_id"] == question_id), None)
    if g is None:
        raise ValueError(f"no genome for {question_id}")
    ops = [op for op in REGISTRY.values() if mode in op.modes and op.is_applicable(q, g)[0]]
    ops.sort(key=lambda op: (-op.structural_rank, op.id))
    ctx = {"all_genomes": list(genomes), "difficulty_direction": difficulty_direction}
    specs, notes = [], []
    index = 0
    while len(specs) < count and ops and index < count * 4:
        op = ops[index % len(ops)]
        spec = build_spec(op, q, g, mode=mode, seed=seed, index=index // len(ops), ctx=ctx)
        if spec is not None and spec["spec_id"] not in {s["spec_id"] for s in specs}:
            specs.append(spec)
        index += 1
    if len({s["operator"] for s in specs}) < len(specs):
        notes.append("Some operators were reused with different parameters because fewer distinct operators were applicable.")
    if len(specs) < count:
        notes.append(f"Only {len(specs)} variant spec(s) could be planned for {question_id}.")
    return {
        "schema_version": SCHEMA_VERSION,
        "plan_id": stable_id("plan", seed, mode, [s["spec_id"] for s in specs]),
        "seed": seed,
        "mode": mode,
        "specs": specs,
        "skipped": [],
        "notes": notes,
    }
