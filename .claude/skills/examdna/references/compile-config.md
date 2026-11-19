# Compile configuration — `compile_config.json`

Only `total_marks` is required. With an Exam DNA profile and no `sections`, sections are derived from the blueprint's mark shares (scaled, largest-remainder rounding) and each section accepts the question types observed in it.

| Key | Meaning |
| --- | --- |
| `title`, `subject`, `language` (`en`/`tr`), `time_minutes`, `instructions` | Presentation. Only state a time the user gave or that you estimated and labelled. |
| `total_marks` | Hard: exact total. |
| `question_count` | Hard: exact number of questions (optional). Otherwise a soft target scaled from the blueprint. |
| `sections[]` | `label`, `marks` (hard), optional `question_count` / `min_questions` / `max_questions`, `allowed_types`, `source_sections`, `title`, `instructions`. Section marks must sum to `total_marks`. |
| `allowed_topics`, `excluded_topics` | Hard topic filters. |
| `required_topics`, `required_types` | Hard: each must appear at least once. |
| `difficulty_target` | Soft target shares `{foundation, standard, challenging}`. |
| `difficulty_shift` | −2..+2: shift the blueprint's difficulty shares by bands (+1 = harder). |
| `max_per_family` | Hard: max questions descending from the same source question (default 1). |
| `include_review_required` | Allow flagged questions (default false). They stay flagged in the answer key. |
| `include_source_questions` | Allow original source questions (default false). |
| `seed` | Deterministic tie-breaking; same pool + config + seed ⇒ same exam. |
| `search_budget` | Node limit for the search (default 200 000). |
| `weights` | Soft-objective weights: `topic` 1.0, `cognitive` 0.5, `difficulty` 0.75, `question_type` 0.5, `family_repeat` 0.5, `question_count` 0.5. |

The solver reports whether the search was exhaustive. Only an exhaustive search is "best under the stated objective" — never claim educational optimality.

When infeasible, `compile_diagnosis.json` gives per-section reachable mark totals, missing required topics/types, excluded-question counts and concrete suggestions. Explain them; do not silently relax constraints.
