# Validation methods

Each check returns `{stage, check, status, method, message}`. Status ∈ `PASS`, `FAIL`, `REVIEW_REQUIRED`, `NOT_VERIFIED`, `INFO`. Method ∈ `deterministic`, `model_assisted`, `human`.

**Aggregation:** any `FAIL` → `FAIL`; else any `REVIEW_REQUIRED`/`NOT_VERIFIED` → `REVIEW_REQUIRED`; else `PASS`. `INFO` never changes the state. Only `PASS` questions are used by the compiler unless `include_review_required` is set; `FAIL` questions never enter the pool.

## Stages

| Stage | Checks |
| --- | --- |
| schema | candidate, question and genome schemas; reasoning graph validity; unique question ID |
| lineage | spec exists; parent and operator match the spec; operator registered; parent and its genome exist; candidate's own lineage does not contradict |
| structural | marks present; part marks sum; duplicate part labels; MC has ≥2 options with unique keys |
| answer_marking | marking points total = marks (and per part); answer present; MC key is an option; MC key shows the verified value; final-answer text contains the verified value; qualitative answers need human review |
| numeric | expression present; all names defined (else *missing information*); verification variables equal the stated givens (raw or SI-converted); exact/float recomputation vs claimed value (default relative tolerance 1 %); unit dimension of the expression vs claimed unit; domain limits on variables or result |
| ambiguity | contradictory numeric constraints; givens violating constraints; values used but not stated; figures/graphs/tables referenced but not supplied; multiple valid answers without an accept rule; vague wording (INFO); unused givens (INFO) |
| invariants | each `preserve` property unchanged; each `must_change` property changed (difficulty: in the requested direction); each `required_judgements` item supplied and positive |
| distance | concept-set drift within the mode cap; not a near-duplicate of the parent |
| duplicates | not a near-verbatim copy of any source question (≥ 0.85); not a duplicate of an already-accepted candidate |
| security | instruction-like text in the question |

## Safe recomputation

Expressions are parsed with `ast` and evaluated by a whitelist walker: numbers, variables, `+ − × ÷ ** %`, unary signs and `sqrt sin cos tan asin acos atan atan2 exp log ln log10 abs radians degrees min max`, constant `pi`. Attribute access, subscripts, lambdas, comprehensions, keyword arguments and unknown names are rejected; exponents are bounded (|n| ≤ 64), length ≤ 500 characters. When only rational operations are used, evaluation is exact with `fractions.Fraction` (decimal literals converted exactly).

## Units

A small SI algebra (M, L, T, I, Θ, N) with prefixes G M k c m µ n and units kg g t m s min h A K mol N J eV W Pa Hz C V Ω/ohm F T L rad deg %. Dimensional analysis walks the expression: addition requires equal dimensions, multiplication adds them, powers need numeric exponents, `sqrt` halves even dimensions, transcendental functions require dimensionless arguments. Unknown units give `NOT_VERIFIED`, never a guess.

## What is not verified

- Correctness of non-numeric answers and explanations (→ `REVIEW_REQUIRED` unless human-reviewed).
- That the expression is the *right* physics for the question — only that it is consistent with the givens, the claimed value and the units. The agent's `target_skill` judgement is model-assisted.
- Symbolic answers, proofs, graphs and diagrams.
