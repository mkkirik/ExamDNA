# Question genome format (schema 0.1.0)

Formal schema: [`examdna/schemas/genome.schema.json`](../examdna/schemas/genome.schema.json). Print it with `examdna schema genome`.

| Section | Fields | Typical provenance |
| --- | --- | --- |
| identity | `genome_id`, `question_id`, `parent_question_id`, `provenance` (origin, document, page), `lineage[]` (question_id, operator, spec_id) | calculated |
| knowledge | `primary_concept`, `secondary_concepts`, `prerequisites`, `learning_objectives`, `topic`, `subtopic` | inferred (agent) / explicit (objectives from a syllabus) |
| reasoning | `steps[]` (`id`, `type`, `description`), `edges[]` (pairs), `expected_inference`, `justification_required` | inferred |
| representation | `input[]` (verbal, table, graph, equation, diagram, symbolic, data_set), `output[]`, `context` | inferred / calculated default |
| constraints | `explicit`, `implicit`, `domain`, `boundary`, `units`, `precision` | explicit / inferred |
| assessment | `command_term`, `question_type`, `cognitive_level`, `max_marks`, `answer_type`, `answer_unit`, `expected_answer`, `marking_components`, `difficulty_features`, `difficulty` | mixed |
| validation | `structural_completeness` (complete/partial/minimal), `missing_components`, `solvability`, `answer_validation`, `uniqueness`, `human_review_required`, `confidence`, `graph_errors` | calculated |
| field_provenance | map of field path → provenance | calculated |

## Reasoning graph

A directed acyclic graph. Step types: `read_given`, `read_representation`, `recall_fact`, `identify_concept`, `identify_constraint`, `convert_units`, `construct_model`, `select_relation`, `apply_mathematics`, `derive_result`, `compare`, `interpret_result`, `justify`, `evaluate`.

`analyze_reasoning_graph` reports: validity (unknown nodes, self-loops, cycles, duplicate IDs), deterministic topological order (Kahn, lexical ties), step-type sequence, linearity, branch and join points, sources and sinks.

## Completeness rules

- `minimal`: missing `primary_concept` or reasoning steps — the planner skips such questions.
- `partial`: missing learning objectives, marks, answer type or marking components.
- `complete`: none missing.

Nothing is fabricated: if the agent does not annotate a field it stays empty and is listed in `missing_components`.

## Versioning

`schema_version` follows `0.1.x`. Additive optional fields bump the patch version; renamed or removed fields bump the minor version and need a migration note in CHANGELOG.md.
