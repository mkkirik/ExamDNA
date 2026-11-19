"""Controlled vocabularies shared by every module.

Schema keys and identifiers are always English; user-facing text may be in any
language.
"""

QUESTION_TYPES = [
    "multiple_choice",
    "short_answer",
    "calculation",
    "extended_response",
    "data_interpretation",
    "diagram_interpretation",
    "graph_interpretation",
    "mixed",
]

QUESTION_TYPE_ALIASES = {
    "mcq": "multiple_choice",
    "multiple-choice": "multiple_choice",
    "multiplechoice": "multiple_choice",
    "mc": "multiple_choice",
    "short": "short_answer",
    "short-answer": "short_answer",
    "calc": "calculation",
    "numerical": "calculation",
    "numeric": "calculation",
    "extended": "extended_response",
    "essay": "extended_response",
    "long_answer": "extended_response",
    "data": "data_interpretation",
    "data-analysis": "data_interpretation",
    "diagram": "diagram_interpretation",
    "graph": "graph_interpretation",
    "structured": "mixed",
}

COGNITIVE_LEVELS = [
    "recall",
    "interpretation",
    "application",
    "multi_step_reasoning",
    "evaluation",
    "synthesis",
]

REPRESENTATIONS = ["verbal", "table", "graph", "equation", "diagram", "symbolic", "data_set"]

# Compatible representation transformations for the representation operator.
REPRESENTATION_TRANSFORMS = {
    "verbal": ["table", "equation", "graph"],
    "table": ["graph", "verbal"],
    "equation": ["graph", "verbal"],
    "graph": ["table", "verbal"],
    "diagram": ["table", "verbal"],
    "symbolic": ["verbal", "graph"],
    "data_set": ["table", "graph"],
}

REASONING_STEP_TYPES = [
    "read_given",
    "read_representation",
    "recall_fact",
    "identify_concept",
    "identify_constraint",
    "convert_units",
    "construct_model",
    "select_relation",
    "apply_mathematics",
    "derive_result",
    "compare",
    "interpret_result",
    "justify",
    "evaluate",
]

ANSWER_TYPES = ["numeric", "choice", "short_text", "extended_text", "expression", "graph_sketch", "mixed"]

QUESTION_TYPE_TO_ANSWER_TYPE = {
    "multiple_choice": "choice",
    "short_answer": "short_text",
    "calculation": "numeric",
    "extended_response": "extended_text",
    "data_interpretation": "mixed",
    "diagram_interpretation": "mixed",
    "graph_interpretation": "mixed",
    "mixed": "mixed",
}

COMMAND_TERMS = [
    "show that",
    "calculate",
    "determine",
    "estimate",
    "deduce",
    "derive",
    "explain",
    "describe",
    "outline",
    "state",
    "define",
    "identify",
    "sketch",
    "draw",
    "compare",
    "evaluate",
    "discuss",
    "suggest",
    "predict",
    "justify",
]

PROVENANCE_KINDS = ["explicit", "inferred", "calculated", "unverified"]
CONFIDENCE_LEVELS = ["high", "medium", "low"]
REVIEW_STATUSES = ["unreviewed", "needs_review", "human_reviewed"]

PASS = "PASS"
FAIL = "FAIL"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
NOT_VERIFIED = "NOT_VERIFIED"
VALIDATION_STATES = [PASS, FAIL, REVIEW_REQUIRED, NOT_VERIFIED]

MUTATION_MODES = ["conservative", "balanced", "exploratory"]
DIFFICULTY_BANDS = ["foundation", "standard", "challenging"]

DISTANCE_DIMENSIONS = ["surface", "concept", "reasoning", "representation", "constraint", "answer"]
