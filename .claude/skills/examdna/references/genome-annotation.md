# Genome annotations — `annotations.json`

`{"annotations": {"<question id>": { ...annotation... }}}`. Annotations are merged with the question by `genome` / `prepare`; anything you annotate gets provenance `inferred`.

```json
{
  "knowledge": {
    "primary_concept": "uniformly accelerated motion",
    "secondary_concepts": ["friction"],
    "prerequisites": ["acceleration", "velocity"]
  },
  "reasoning": {
    "steps": [
      {"id": "s1", "type": "read_given"},
      {"id": "s2", "type": "identify_constraint", "description": "final velocity is zero"},
      {"id": "s3", "type": "select_relation", "description": "v² = u² − 2as"},
      {"id": "s4", "type": "apply_mathematics"},
      {"id": "s5", "type": "derive_result"},
      {"id": "s6", "type": "justify", "description": "explain effect of wet road"}
    ],
    "edges": [["s1","s2"],["s2","s3"],["s3","s4"],["s4","s5"],["s2","s6"]],
    "justification_required": true
  },
  "representation": {"input": ["verbal"], "context": "road transport"},
  "constraints": {"explicit": ["deceleration is uniform"], "implicit": [], "boundary": ["final velocity is zero"]},
  "assessment": {"difficulty_features": {"math_complexity": 2}}
}
```

## Step types

`read_given`, `read_representation`, `recall_fact`, `identify_concept`, `identify_constraint`, `convert_units`, `construct_model`, `select_relation`, `apply_mathematics`, `derive_result`, `compare`, `interpret_result`, `justify`, `evaluate`.

- The graph must be acyclic. Branches (one step feeding two) are allowed and expected for multi-part questions.
- Describe the *intended* solution path, not every possible one.
- Keep concept names consistent across questions (same string for the same concept) — comparison and fusion depend on it.

## Representations

`verbal`, `table`, `graph`, `equation`, `diagram`, `symbolic`, `data_set`.

## math_complexity (0–3)

0 none (recall) · 1 single substitution · 2 rearrangement or two linked relations · 3 roots/powers/simultaneous or trigonometric manipulation.

## Heuristic difficulty (computed, not annotated)

`points = min(stages,6) + min(prerequisites,4) + 2·math_complexity + min(explicit+boundary constraints,4) + min(representations−1,3)`; bands: foundation ≤ 6, standard 7–12, challenging ≥ 13. This is a transparent heuristic, not a validated difficulty measure.
