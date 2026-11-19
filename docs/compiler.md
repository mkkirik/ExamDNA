# Exam compiler

Input: a validated pool (`validated_pool.json`), a config (`compile_config.json`, schema `compile_config`), optionally an Exam DNA profile. Option reference: [`.claude/skills/examdna/references/compile-config.md`](../.claude/skills/examdna/references/compile-config.md).

## Hard constraints

Exact total marks; exact section marks (sections sum to the total); per-section question count / min / max; allowed types per section; `source_sections` matching; unique questions; `max_per_family` (questions sharing a lineage root); allowed / excluded topics; required topics and types; exact total question count if given; validation state (`PASS`, plus `REVIEW_REQUIRED` only if allowed); generated questions only unless `include_source_questions`.

## Soft objective

`cost = Σ wᵢ · TV(exam distributionᵢ, targetᵢ) + w_family · repeats/n + w_count · |n − n_target|/n_target` over topic, cognitive level, heuristic difficulty band and question type (mark-weighted). Targets come from the Exam DNA (topic targets filtered by allowed/excluded topics) or the config (`difficulty_target`, `difficulty_shift`). Default weights: topic 1.0, cognitive 0.5, difficulty 0.75, question type 0.5, family repeat 0.5, question count 0.5.

## Algorithm

1. Filter the pool; record exclusion reasons.
2. Per section, enumerate exact-sum combinations depth-first over items in seeded hash order with suffix-sum pruning (≤ 4000 combinations per section; truncation is reported).
3. Combine sections depth-first (cheapest section combinations first), rejecting overlaps and family excess; evaluate complete exams; keep the lowest cost (first found wins ties). Stop at `search_budget` nodes.
4. Report `nodes_explored`, `exhaustive`, and either "best possible under the stated objective" (exhaustive) or "best found within limits; optimality not established".

Determinism: the same pool, config and seed always give the same exam (tested).

## Infeasibility

`CompilationInfeasible.diagnosis` (CLI exit code 2, `compile_diagnosis.json`) includes: the failing condition, eligible questions and marks, exclusion counts by reason, per-section reachable mark totals (nearest below/above via subset-sum), available types, missing required topics/types, and concrete suggestions (adjust marks, allow review-required items, generate questions for a topic/type, raise `max_per_family`). The compiler never silently relaxes a hard constraint.
