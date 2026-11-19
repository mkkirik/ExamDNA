# Mutation operators

Live contracts: `examdna operators` or `examdna operators --json`.

## Two-stage generation

1. **Stage A — planning (deterministic).** `plan_mutations` chooses applicable operators for each target question (balanced across the bank by usage count, ordered by a seeded hash) and builds a spec: operator, concrete parameters, `preserve`, `must_change`, `may_change`, invariants, `required_judgements`, instructions, validation checks and known failure modes. Same inputs + seed ⇒ identical plan.
2. **Stage B — generation (agent).** Claude writes one candidate per spec as JSON (question + genome + verification + judgements).
3. **Validation (deterministic).** See [validation.md](validation.md).

## Operators

| ID | Modes | Applicable when | Parameters chosen by the planner |
| --- | --- | --- | --- |
| `surface` | all | primary concept known | rewriting style |
| `parameter` | all | ≥1 numeric given | 1–2 givens with suggested values (× 0.5/0.75/1.25/1.5/2, rounded to the original significant figures, sign kept, numeric constraints respected) |
| `representation` | all | concept known; not data-free MC | `from` → `to` using the compatibility map (verbal→table/equation/graph, table→graph/verbal, …) |
| `context_transfer` | all | concept known | target context from a fixed library, different from the current one |
| `constraint` | balanced, exploratory | numeric givens or explicit constraints | `add` or `modify` (+ target constraint) |
| `reverse` | balanced, exploratory | ≥2 reasoning steps and a numeric given | which given becomes the unknown |
| `difficulty` | balanced, exploratory | reasoning steps present | direction (`up`/`down`), adjustment kind, current heuristic points, minimum change |
| `reasoning_path` | balanced, exploratory | ≥2 reasoning steps | parent step-type sequence that must not be reproduced |
| `fusion` | exploratory | a partner genome exists with the same topic or a prerequisite/secondary link | partner question and concept |

`plan_variants(question, N)` takes applicable operators in decreasing structural rank (fusion, reverse, difficulty/reasoning path, representation, constraint, context, parameter, surface) so that N variants differ in structure, not just wording; it reuses operators with new parameters only when fewer than N are applicable and says so.

## Adding an operator

1. Define a `MutationOperator` in `examdna/mutation/operators.py` with `register(...)`. Use only property names from `PROPERTIES`; `preserve` and `must_change` must not overlap.
2. Add a parameter builder to `PARAM_BUILDERS` in `planner.py` (deterministic; use only the supplied `rng`).
3. If it needs a new checkable property, add a checker to `UNCHANGED` in `mutation/properties.py`.
4. Add tests: applicability, planning determinism, and at least one valid and one invalid candidate.
5. Document it here and in `.claude/skills/examdna/references/mutation-operators.md`.
