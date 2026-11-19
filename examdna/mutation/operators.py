"""Mutation-operator registry.

Each operator is a *contract*: what it may change, what it must change, what
it must preserve, and how the result is checked. Operators never write
question text — the agent does that from a mutation spec — but applicability
and checks are deterministic.

Property vocabulary (used in ``preserve`` / ``must_change`` / ``may_change``):

=====================  =====================================================
primary_concept        genome.knowledge.primary_concept (case-insensitive)
learning_objectives    parent objectives ⊆ child objectives
topic                  question.topic
question_type          question.question_type
answer_type            genome.assessment.answer_type
marks                  question.marks
reasoning_structure    step-type sequence of the reasoning graph
representation         set of input representations
numeric_parameters     values of ``given`` entries, by symbol
constraints            content words of explicit/domain/boundary constraints
context                genome.representation.context (semantic if absent)
wording                question text (word 3-shingle similarity < 0.8)
reasoning_direction    some parent given becomes the unknown
difficulty_features    heuristic difficulty points move in requested direction
concept_set            child concept set strictly contains parent concepts
=====================  =====================================================
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

PROPERTIES = [
    "primary_concept",
    "learning_objectives",
    "topic",
    "question_type",
    "answer_type",
    "marks",
    "reasoning_structure",
    "representation",
    "numeric_parameters",
    "constraints",
    "context",
    "wording",
    "reasoning_direction",
    "difficulty_features",
    "concept_set",
]

CORE = ["primary_concept", "learning_objectives", "topic"]


def _numeric_givens(q: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [g for g in q.get("given") or [] if isinstance(g.get("value"), (int, float)) and g.get("role") != "constant"]


def _steps(g: Dict[str, Any]) -> List[Dict[str, Any]]:
    return (g.get("reasoning") or {}).get("steps") or []


@dataclass
class MutationOperator:
    id: str
    name: str
    description: str
    required_inputs: List[str]
    applicable_question_types: Optional[List[str]]
    preserve: List[str]
    must_change: List[str]
    may_change: List[str]
    invariants: List[str]
    expected_difficulty_effect: str
    validation_checks: List[str]
    failure_modes: List[str]
    modes: List[str]
    structural_rank: int  # higher = typically larger structural change
    applicability: Callable[[Dict[str, Any], Dict[str, Any]], Tuple[bool, str]] = field(repr=False, default=None)  # type: ignore[assignment]

    def is_applicable(self, question: Dict[str, Any], genome: Dict[str, Any]) -> Tuple[bool, str]:
        qtype = question.get("question_type")
        if self.applicable_question_types is not None and qtype not in self.applicable_question_types:
            return False, f"question type {qtype!r} not supported by {self.id}"
        if self.applicability is None:
            return True, "ok"
        return self.applicability(question, genome)

    def contract(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop("applicability", None)
        return data


def _needs_concept(q, g):
    if not (g.get("knowledge") or {}).get("primary_concept"):
        return False, "genome has no primary concept; annotate the genome first"
    return True, "ok"


def _parameter_ok(q, g):
    if not _numeric_givens(q):
        return False, "no numeric given values to vary"
    return _needs_concept(q, g)


def _representation_ok(q, g):
    ok, why = _needs_concept(q, g)
    if not ok:
        return ok, why
    if q.get("question_type") == "multiple_choice" and not _numeric_givens(q) and not q.get("table"):
        return False, "multiple-choice item without data has nothing to re-represent"
    return True, "ok"


def _constraint_ok(q, g):
    ok, why = _needs_concept(q, g)
    if not ok:
        return ok, why
    if not _numeric_givens(q) and not (g.get("constraints") or {}).get("explicit"):
        return False, "no constraint or numeric condition to modify"
    return True, "ok"


def _reverse_ok(q, g):
    ok, why = _needs_concept(q, g)
    if not ok:
        return ok, why
    if len(_steps(g)) < 2:
        return False, "reasoning has fewer than 2 steps"
    if not _numeric_givens(q):
        return False, "reverse reasoning needs at least one given quantity that can become the unknown"
    return True, "ok"


def _difficulty_ok(q, g):
    ok, why = _needs_concept(q, g)
    if not ok:
        return ok, why
    if not _steps(g):
        return False, "reasoning steps are required to adjust difficulty explicitly"
    return True, "ok"


def _path_ok(q, g):
    ok, why = _needs_concept(q, g)
    if not ok:
        return ok, why
    if len(_steps(g)) < 2:
        return False, "a single-step question has no alternative reasoning path"
    return True, "ok"


REGISTRY: Dict[str, MutationOperator] = {}


def register(op: MutationOperator) -> MutationOperator:
    if op.id in REGISTRY:
        raise ValueError(f"operator {op.id} already registered")
    unknown = [p for p in op.preserve + op.must_change + op.may_change if p not in PROPERTIES]
    if unknown:
        raise ValueError(f"operator {op.id} uses unknown properties {unknown}")
    if set(op.preserve) & set(op.must_change):
        raise ValueError(f"operator {op.id} both preserves and changes {set(op.preserve) & set(op.must_change)}")
    REGISTRY[op.id] = op
    return op


ALL_MODES = ["conservative", "balanced", "exploratory"]
NON_CONSERVATIVE = ["balanced", "exploratory"]

register(MutationOperator(
    id="surface",
    name="Surface Mutation",
    description="Rewrites wording or superficial context while keeping the assessed objective, data and solution path.",
    required_inputs=["question", "genome"],
    applicable_question_types=None,
    preserve=CORE + ["question_type", "answer_type", "marks", "reasoning_structure", "representation", "numeric_parameters", "constraints"],
    must_change=["wording"],
    may_change=["context"],
    invariants=["Identical solution path and answer", "No information added or removed"],
    expected_difficulty_effect="none",
    validation_checks=["schema", "wording_changed", "invariants", "numeric_recompute", "near_duplicate"],
    failure_modes=["trivial synonym swap (near-duplicate)", "accidental change of given data", "lost information"],
    modes=ALL_MODES,
    structural_rank=0,
    applicability=_needs_concept,
))

register(MutationOperator(
    id="parameter",
    name="Parameter Mutation",
    description="Changes numerical values of given quantities; the answer is recomputed and checked.",
    required_inputs=["question", "genome", "numeric givens"],
    applicable_question_types=None,
    preserve=CORE + ["question_type", "answer_type", "marks", "reasoning_structure", "representation", "constraints"],
    must_change=["numeric_parameters"],
    may_change=["wording"],
    invariants=["Answer recomputed from the new values", "Values stay inside physical/domain limits", "Same units"],
    expected_difficulty_effect="none",
    validation_checks=["schema", "numeric_recompute", "units", "domain", "givens_consistent"],
    failure_modes=["answer not updated", "values inconsistent with each other", "out-of-domain values (e.g. negative mass)"],
    modes=ALL_MODES,
    structural_rank=1,
    applicability=_parameter_ok,
))

register(MutationOperator(
    id="representation",
    name="Representation Mutation",
    description="Presents the same information in a compatible representation (e.g. table → graph, verbal → equation).",
    required_inputs=["question", "genome", "target representation"],
    applicable_question_types=None,
    preserve=CORE + ["answer_type"],
    must_change=["representation"],
    may_change=["wording", "question_type", "reasoning_structure", "marks", "numeric_parameters"],
    invariants=["All information needed to solve is present in the new representation", "Representation is legible in print"],
    expected_difficulty_effect="variable",
    validation_checks=["schema", "representation_changed", "invariants", "numeric_recompute", "diagram_specified"],
    failure_modes=["information lost in conversion", "graph/table underspecified", "representation unreadable in text output"],
    modes=ALL_MODES,
    structural_rank=4,
    applicability=_representation_ok,
))

register(MutationOperator(
    id="constraint",
    name="Constraint Mutation",
    description="Modifies an explicit condition or introduces a justified new condition; solvability is re-checked.",
    required_inputs=["question", "genome"],
    applicable_question_types=["calculation", "short_answer", "extended_response", "data_interpretation", "mixed", "graph_interpretation"],
    preserve=CORE + ["answer_type"],
    must_change=["constraints"],
    may_change=["numeric_parameters", "reasoning_structure", "wording", "marks"],
    invariants=["Question remains solvable", "Constraints are mutually consistent", "Givens satisfy every constraint"],
    expected_difficulty_effect="variable",
    validation_checks=["schema", "constraints_changed", "constraint_consistency", "numeric_recompute", "domain"],
    failure_modes=["contradictory constraints", "constraint makes question unsolvable", "constraint irrelevant to solution"],
    modes=NON_CONSERVATIVE,
    structural_rank=3,
    applicability=_constraint_ok,
))

register(MutationOperator(
    id="reverse",
    name="Reverse Reasoning Mutation",
    description="Inverts the direction of reasoning: a former result is given and a former input must be found.",
    required_inputs=["question", "genome", "numeric givens"],
    applicable_question_types=None,
    preserve=CORE,
    must_change=["reasoning_direction"],
    may_change=["answer_type", "reasoning_structure", "numeric_parameters", "wording", "marks", "question_type"],
    invariants=["The original unknown becomes given data", "If several answers are valid the marking defines an accept rule, otherwise reject"],
    expected_difficulty_effect="increase",
    validation_checks=["schema", "direction_changed", "numeric_recompute", "uniqueness", "domain"],
    failure_modes=["non-unique answer without accept rule", "reverse problem has no solution in domain", "same direction disguised"],
    modes=NON_CONSERVATIVE,
    structural_rank=6,
    applicability=_reverse_ok,
))

register(MutationOperator(
    id="context_transfer",
    name="Context Transfer",
    description="Moves the same concept and reasoning into a different authentic application context.",
    required_inputs=["question", "genome", "target context"],
    applicable_question_types=None,
    preserve=CORE + ["answer_type", "reasoning_structure", "question_type", "marks"],
    must_change=["context", "wording"],
    may_change=["numeric_parameters", "constraints"],
    invariants=["Physics/maths remains valid in the new context", "Values realistic for the new context"],
    expected_difficulty_effect="none",
    validation_checks=["schema", "wording_changed", "context_changed", "invariants", "numeric_recompute"],
    failure_modes=["inauthentic or implausible context", "context changes the required model", "unrealistic values"],
    modes=ALL_MODES,
    structural_rank=2,
    applicability=_needs_concept,
))

register(MutationOperator(
    id="difficulty",
    name="Difficulty Adjustment",
    description="Adds or removes reasoning stages, constraints or interpretation demands in an explainable way.",
    required_inputs=["question", "genome", "direction"],
    applicable_question_types=None,
    preserve=["primary_concept", "learning_objectives", "topic"],
    must_change=["difficulty_features"],
    may_change=["reasoning_structure", "constraints", "marks", "numeric_parameters", "wording", "representation", "answer_type"],
    invariants=["Each added/removed stage is named in change_summary", "Marks reflect the new number of stages"],
    expected_difficulty_effect="per direction",
    validation_checks=["schema", "difficulty_direction", "marks_consistent", "numeric_recompute"],
    failure_modes=["harder-looking wording without structural change", "marks not adjusted", "added stage unrelated to objective"],
    modes=NON_CONSERVATIVE,
    structural_rank=5,
    applicability=_difficulty_ok,
))

register(MutationOperator(
    id="fusion",
    name="Concept Fusion",
    description="Combines the parent's objective with a related partner concept in one coherent question.",
    required_inputs=["question", "genome", "partner genome"],
    applicable_question_types=None,
    preserve=["learning_objectives", "topic"],
    must_change=["concept_set"],
    may_change=["primary_concept", "reasoning_structure", "constraints", "marks", "numeric_parameters", "wording", "representation", "answer_type", "question_type"],
    invariants=["Both concepts are needed to answer", "Combination is educationally meaningful (shared topic or prerequisite link)"],
    expected_difficulty_effect="increase",
    validation_checks=["schema", "concept_set_grew", "numeric_recompute", "marks_consistent"],
    failure_modes=["arbitrary combination", "one concept decorative only", "excessive length"],
    modes=["exploratory"],
    structural_rank=7,
    applicability=_needs_concept,
))

register(MutationOperator(
    id="reasoning_path",
    name="Reasoning Path Mutation",
    description="Assesses the same concept through a different valid method (e.g. energy instead of kinematics).",
    required_inputs=["question", "genome"],
    applicable_question_types=None,
    preserve=CORE + ["answer_type"],
    must_change=["reasoning_structure"],
    may_change=["wording", "numeric_parameters", "representation", "marks", "constraints"],
    invariants=["The new path is valid and different, not a paraphrase", "Target concept still required"],
    expected_difficulty_effect="variable",
    validation_checks=["schema", "reasoning_changed", "invariants", "numeric_recompute"],
    failure_modes=["paraphrase with identical method", "new method bypasses the target concept"],
    modes=NON_CONSERVATIVE,
    structural_rank=5,
    applicability=_path_ok,
))


def get_operator(op_id: str) -> MutationOperator:
    try:
        return REGISTRY[op_id]
    except KeyError as exc:
        raise KeyError(f"unknown mutation operator '{op_id}'. Known: {', '.join(REGISTRY)}") from exc


def list_contracts() -> List[Dict[str, Any]]:
    return [op.contract() for op in REGISTRY.values()]
