# Validation Summary

Report `validation-c954cb358a`

| Candidates | PASS | REVIEW_REQUIRED | FAIL |
| --- | --- | --- | --- |
| 22 | 17 | 1 | 4 |

> PASS means every applicable deterministic check passed and every required semantic judgement was supplied and affirmative. Checks marked model_assisted rely on the agent's judgement, not on independent verification.

## Results

### `c01` — **PASS** · representation of `p1-a2`

Distance from parent: surface high (0.76), concept low (0.33), reasoning low (0.25), representation moderate (0.5), constraint none (0.0), answer none (0.0) → **structural_novelty**

All 14 checks passed.
- _1 check(s) rely on agent judgement (model-assisted)._

### `c02` — **PASS** · reasoning_path of `p1-a3`

Distance from parent: surface moderate (0.62), concept low (0.33), reasoning low (0.33), representation none (0.0), constraint none (0.0), answer moderate (0.5) → **structural_novelty**

All 14 checks passed.
- _1 check(s) rely on agent judgement (model-assisted)._

### `c03` — **PASS** · constraint of `p1-a4`

Distance from parent: surface moderate (0.46), concept low (0.33), reasoning low (0.2), representation none (0.0), constraint high (1.0), answer none (0.0) → **structural_novelty**

- `INFO` [ambiguity/unused_given, deterministic] given value(s) not used by the final expression: Pmax
- _1 check(s) rely on agent judgement (model-assisted)._

### `c04-try1` — **FAIL** · surface of `p1-a6`

Distance from parent: surface high (0.78), concept none (0.0), reasoning none (0.0), representation none (0.0), constraint none (0.0), answer none (0.0) → **parameter_novelty**

- `FAIL` [invariants/preserve:numeric_parameters, deterministic] numeric_parameters was supposed to be preserved but changed
- _1 check(s) rely on agent judgement (model-assisted)._

### `c04-try2` — **PASS** · surface of `p1-a6`

Distance from parent: surface high (0.68), concept none (0.0), reasoning none (0.0), representation none (0.0), constraint none (0.0), answer none (0.0) → **surface_novelty**

All 20 checks passed.
- _1 check(s) rely on agent judgement (model-assisted)._

### `c05` — **PASS** · difficulty of `p2-a2`

Distance from parent: surface moderate (0.52), concept low (0.33), reasoning moderate (0.5), representation none (0.0), constraint none (0.0), answer none (0.0) → **structural_novelty**

- `INFO` [ambiguity/unused_given, deterministic] given value(s) not used by the final expression: m1, v1
- _1 check(s) rely on agent judgement (model-assisted)._

### `c06-try1` — **FAIL** · parameter of `p2-a3`

Distance from parent: surface low (0.05), concept none (0.0), reasoning none (0.0), representation none (0.0), constraint none (0.0), answer none (0.0) → **near_duplicate**

- `FAIL` [distance/novelty, deterministic] candidate is a near-duplicate of its parent
- `FAIL` [duplicates/source_copy, deterministic] near-verbatim copy of source question p2-a3 (surface similarity 0.95)
- _1 check(s) rely on agent judgement (model-assisted)._

### `c06-try2` — **PASS** · parameter of `p2-a3`

Distance from parent: surface moderate (0.61), concept none (0.0), reasoning none (0.0), representation none (0.0), constraint none (0.0), answer none (0.0) → **parameter_novelty**

All 19 checks passed.
- _1 check(s) rely on agent judgement (model-assisted)._

### `c07` — **PASS** · reverse of `p2-a4`

Distance from parent: surface high (0.74), concept none (0.0), reasoning none (0.0), representation none (0.0), constraint none (0.0), answer moderate (0.5) → **structural_novelty**

All 16 checks passed.
- _1 check(s) rely on agent judgement (model-assisted)._

### `c08` — **PASS** · context_transfer of `p2-a5`

Distance from parent: surface moderate (0.62), concept none (0.0), reasoning none (0.0), representation none (0.0), constraint none (0.0), answer none (0.0) → **parameter_novelty**

All 18 checks passed.
- _1 check(s) rely on agent judgement (model-assisted)._

### `c09` — **PASS** · difficulty of `p3-a2`

Distance from parent: surface low (0.31), concept moderate (0.5), reasoning moderate (0.5), representation none (0.0), constraint none (0.0), answer moderate (0.5) → **structural_novelty**

All 13 checks passed.
- _1 check(s) rely on agent judgement (model-assisted)._

### `c10` — **PASS** · context_transfer of `p3-a3`

Distance from parent: surface low (0.32), concept none (0.0), reasoning none (0.0), representation none (0.0), constraint none (0.0), answer none (0.0) → **parameter_novelty**

All 18 checks passed.
- _1 check(s) rely on agent judgement (model-assisted)._

### `c11` — **REVIEW_REQUIRED** · representation of `p3-a4`

Distance from parent: surface moderate (0.5), concept none (0.0), reasoning low (0.25), representation moderate (0.5), constraint none (0.0), answer none (0.0) → **structural_novelty**

- `NOT_VERIFIED` [invariants/judgement:target_skill, deterministic] no agent judgement supplied for target_skill

### `c12-try1` — **FAIL** · parameter of `p1-b1`

Distance from parent: surface moderate (0.62), concept none (0.0), reasoning none (0.0), representation none (0.0), constraint none (0.0), answer none (0.0) → **parameter_novelty**

- `FAIL` [numeric/recompute, deterministic] claimed 4 but recomputed 3.22581 (exact rational arithmetic)
- _1 check(s) rely on agent judgement (model-assisted)._

### `c12-try2` — **PASS** · parameter of `p1-b1`

Distance from parent: surface moderate (0.62), concept none (0.0), reasoning none (0.0), representation none (0.0), constraint none (0.0), answer none (0.0) → **parameter_novelty**

All 21 checks passed.
- _1 check(s) rely on agent judgement (model-assisted)._

### `c13` — **PASS** · surface of `p1-b2`

Distance from parent: surface moderate (0.5), concept none (0.0), reasoning none (0.0), representation none (0.0), constraint none (0.0), answer none (0.0) → **surface_novelty**

All 21 checks passed.
- _1 check(s) rely on agent judgement (model-assisted)._

### `c14-try1` — **FAIL** · reverse of `p1-b3`

Distance from parent: surface moderate (0.4), concept none (0.0), reasoning none (0.0), representation none (0.0), constraint none (0.0), answer moderate (0.5) → **structural_novelty**

- `INFO` [ambiguity/vague_terms, deterministic] vague wording: suitable value
- `FAIL` [ambiguity/uniqueness, deterministic] several answers are valid but no marking accept_rule is defined
- _1 check(s) rely on agent judgement (model-assisted)._

### `c14-try2` — **PASS** · reverse of `p1-b3`

Distance from parent: surface low (0.31), concept none (0.0), reasoning low (0.33), representation none (0.0), constraint none (0.0), answer moderate (0.5) → **structural_novelty**

All 15 checks passed.
- _1 check(s) rely on agent judgement (model-assisted)._

### `c15` — **PASS** · reasoning_path of `p2-b1`

Distance from parent: surface moderate (0.36), concept low (0.25), reasoning high (0.81), representation none (0.0), constraint moderate (0.5), answer moderate (0.5) → **structural_novelty**

All 15 checks passed.
- _1 check(s) rely on agent judgement (model-assisted)._

### `c16` — **PASS** · constraint of `p2-b3`

Distance from parent: surface moderate (0.46), concept low (0.33), reasoning low (0.29), representation none (0.0), constraint high (1.0), answer none (0.0) → **structural_novelty**

- `INFO` [ambiguity/unused_given, deterministic] given value(s) not used by the final expression: I2, t
- _1 check(s) rely on agent judgement (model-assisted)._

### `c17` — **PASS** · difficulty of `p3-b1`

Distance from parent: surface moderate (0.58), concept moderate (0.5), reasoning low (0.25), representation none (0.0), constraint high (0.73), answer moderate (0.5) → **structural_novelty**

- `INFO` [ambiguity/unused_given, deterministic] given value(s) not used by the final expression: a
- _1 check(s) rely on agent judgement (model-assisted)._

### `c18` — **PASS** · representation of `p3-b2`

Distance from parent: surface low (0.33), concept low (0.25), reasoning low (0.14), representation moderate (0.5), constraint none (0.0), answer moderate (0.5) → **structural_novelty**

- `INFO` [ambiguity/unused_given, deterministic] given value(s) not used by the final expression: t
- _1 check(s) rely on agent judgement (model-assisted)._
