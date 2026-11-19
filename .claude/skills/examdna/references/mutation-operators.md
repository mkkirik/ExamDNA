# Mutation operators

Run `examdna_cli.py operators` for the live contracts. Each spec lists `preserve`, `must_change`, `may_change`, `invariants`, `required_judgements` and operator-specific `parameters`.

| Operator | Modes | Must change | Key preserved | Typical failure |
| --- | --- | --- | --- | --- |
| `surface` | all | wording | concept, objectives, data, method, marks | near-duplicate wording |
| `parameter` | all | given values | method, constraints, marks | answer not recomputed; copied wording |
| `representation` | all | input representation | concept, objectives, answer type | information lost; undescribed graph |
| `context_transfer` | all | context + wording | method, marks, question type | implausible context |
| `constraint` | balanced, exploratory | constraints | concept, answer type | contradictory / irrelevant constraint |
| `reverse` | balanced, exploratory | reasoning direction (a former given becomes the unknown) | concept, objectives | several valid answers without an accept rule |
| `difficulty` | balanced, exploratory | heuristic difficulty points (direction from spec) | concept, objectives | "harder wording" with no structural change |
| `reasoning_path` | balanced, exploratory | step-type sequence | concept, answer type | paraphrase with the same method |
| `fusion` | exploratory | concept set grows | parent objectives | arbitrary combination |

## Property checks

Deterministic: primary concept, objectives (parent ⊆ child), topic, question type, answer type, marks, reasoning step sequence, representation set, given values, constraint words, wording (word-sequence similarity < 0.8), reasoning direction (a parent given symbol is absent), difficulty points, concept set.
Semantic (you must judge in `invariant_judgements`): `target_skill` always; `context` for context operators when not checkable; `both_concepts_required` for fusion.

## Writing good candidates

- Keep the parent's `section`, `topic` and learning objectives (you may add objectives).
- Copy the parent's genome where it must be preserved (same step types, same constraint wording, same answer type) and change only what the spec allows.
- Recompute every numeric answer; put the formula in `verification.expression` using the `given` symbols.
- Write fresh wording. Text that is ≥ 85 % similar to any source question is rejected as a near-verbatim copy.
- Marking points must sum to the marks (and per part).
- If a spec cannot be satisfied sensibly (e.g. an inauthentic context), say so and skip it rather than forcing a bad question.
