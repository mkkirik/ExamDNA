# Candidate format — `candidates.json`

`{"candidates": [ candidate, ... ]}`. One candidate per spec; a retry for the same spec gets a new `candidate_id`.
Template: `assets/candidate_template.json`. Schema: `schemas/candidate.schema.json`.

```json
{
  "candidate_id": "c12",
  "spec_id": "spec-1dda8598d2",
  "parent_id": "p1-b1",
  "operator": "parameter",
  "question": {
    "id": "m-p1-b1-par",
    "subject": "Physics", "topic": "Kinematics", "subtopic": "Stopping distance",
    "text": "Travelling along a straight road at 20 m/s, a driver applies the brakes. The car decelerates uniformly and stops after covering 62 m.",
    "question_type": "mixed", "marks": 7, "section": "B",
    "learning_objectives": ["K1 Use the equations of uniformly accelerated motion"],
    "cognitive_level": "multi_step_reasoning",
    "given": [{"symbol": "u", "value": 20, "unit": "m/s"}, {"symbol": "s", "value": 62, "unit": "m"}],
    "constraints": [{"text": "deceleration is uniform", "kind": "explicit"}],
    "parts": [{"label": "a", "text": "Find the size of the car's deceleration.", "marks": 3}, "..."],
    "marking": {"final_answer": "(a) 3.2 m/s² (b) 6.2 s ...", "worked_solution": "...",
                "points": [{"description": "v² = u² − 2as with v = 0", "marks": 1, "part": "a"}, "..."]}
  },
  "genome": {
    "schema_version": "0.1.0", "genome_id": "g-m-p1-b1-par", "question_id": "m-p1-b1-par",
    "knowledge": {"primary_concept": "uniformly accelerated motion", "secondary_concepts": [], "prerequisites": [], "learning_objectives": ["K1 ..."]},
    "reasoning": {"steps": [{"id": "s1", "type": "read_given"}, "..."], "edges": [["s1", "s2"], "..."]},
    "representation": {"input": ["verbal"], "context": "road transport"},
    "constraints": {"explicit": ["deceleration is uniform"], "boundary": ["final velocity is zero"]},
    "assessment": {"answer_type": "mixed", "difficulty_features": {"math_complexity": 2}},
    "validation": {}
  },
  "verification": {
    "kind": "numeric",
    "expression": "u**2/(2*s)",
    "variables": {"u": 20, "s": 62},
    "claimed_value": 3.226,
    "claimed_unit": "m/s^2",
    "relative_tolerance": 0.01,
    "domain": [{"var": "result", "min": 0}],
    "answer_uniqueness": "unique"
  },
  "invariant_judgements": [
    {"property": "target_skill", "preserved": true, "rationale": "Still assesses v² = u² − 2as with v = 0."}
  ],
  "change_summary": "Braking distance changed to 62 m; answers recomputed; reworded."
}
```

## Verification block

- `expression`: arithmetic only — `+ - * / ** %`, parentheses, numbers, variable names, and `sqrt sin cos tan asin acos atan atan2 exp log ln log10 abs radians degrees min max`, constant `pi`. No other code.
- `variables` must equal the question's `given` values (or their SI conversions). Values used but not stated in the question are flagged.
- The engine recomputes the value (exactly with fractions when possible), compares it with `claimed_value` and with the numbers in `marking.final_answer`, checks the unit's physical dimension against the expression, and checks `domain` limits (`var` may be `"result"`).
- `answer_uniqueness`: `unique`, `multiple` (requires `marking.accept_rule`), or `unknown` (→ review).
- Non-numeric answers: use `"kind": "qualitative"`; they remain `REVIEW_REQUIRED` until a human reviews them. For multiple choice without numeric verification, add a judgement `{"property": "answer_correct", "preserved": true}` (model-assisted).
