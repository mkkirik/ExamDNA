# Methodology: Exam DNA, difficulty, comparison and distance

All measures here are transparent and deterministic. None is a psychometric measure, and none has been validated against student performance data.

## Exam DNA

Input: a normalized bank. Generated questions are excluded. Papers are grouped by `source.document`.

- **Per paper**: question count; total marks (only if every question has marks, otherwise `null` and the paper is "incomplete"); sections with marks; ordering (section, type, marks).
- **Aggregate**: `n`, mean, median, min, max of questions per paper, marks per complete paper, marks per question.
- **Sections**: for each label — papers present, question-count and marks summaries, mark share (section marks ÷ total marks over complete papers), marks per question, observed question types, evidence IDs.
- **Distributions** (topic, subtopic, question type, cognitive level, learning objective, heuristic difficulty band): counts, share by count, share by marks, unclassified IDs, evidence IDs per category.
- **Sequencing**: frequency of section orders; per section, in how many papers marks are non-decreasing.
- **Concept combinations**: unordered pairs of concepts (primary + secondary) co-occurring in one question's genome.
- **Structural constraints (blueprint)**: target total marks = median of complete papers; target question count = median; section order; section mark shares.
- **Uncertainty**: evidence level by number of papers — `insufficient` (≤1), `limited` (2–3), `moderate` (4–9), `substantial` (≥10) — plus notes on missing marks, missing topics, missing difficulty features, low-confidence extraction, missing genomes.

## Heuristic difficulty model (`examdna-heuristic-v1`)

```
points = min(reasoning_stages, 6) + min(prerequisite_count, 4) + 2·math_complexity (0..3)
       + min(explicit + boundary constraints, 4) + min(representations − 1, 3)      range 0..23
band   = foundation (≤ 6) · standard (7–12) · challenging (≥ 13)
```

`reasoning_stages` counts reasoning-graph steps except `read_given`. `math_complexity` is the agent's annotation (0 none, 1 substitution, 2 rearrangement/two relations, 3 roots/powers/trigonometry). Its purpose is to make "harder"/"easier" concrete and checkable (the difficulty operator must move the points in the requested direction), not to estimate how many students will answer correctly.

## Genome comparison (similarities in [0, 1], rounded to 2 decimals)

| Dimension | Definition |
| --- | --- |
| concept | Jaccard of {primary} ∪ secondary concepts (case-insensitive) |
| learning_objectives | Jaccard of objective strings |
| reasoning | 1 − normalized Levenshtein distance between step-type sequences in topological order; ×0.5 if one graph is linear and the other branched |
| representation | Jaccard of input representation sets |
| constraint | Jaccard of content words of explicit, domain and boundary constraints |
| answer | 0.5·[answer types equal] + 0.5·[answer units have the same physical dimension] (0.25 if one unit is unknown) |
| surface | `difflib.SequenceMatcher` ratio over lower-cased word tokens |

Limitations: concept and constraint similarity depend on consistent naming by the annotator; the reasoning measure ignores step descriptions; surface similarity is lexical and blind to meaning.

## Mutation distance

distance = 1 − similarity, per dimension; labels `none` < 0.05 ≤ `low` < 0.34 ≤ `moderate` < 0.67 ≤ `high`. Dimensions are never combined into one score.

Novelty class: `structural_novelty` (any of reasoning/representation/constraint/answer ≥ low) · `parameter_novelty` (given values and wording changed, structure not) · `surface_novelty` (wording only) · `near_duplicate` (surface distance < 0.2 and no structural change → rejected). Conceptual equivalence is reported only as a model-assisted judgement when the agent supplied one; otherwise `unverified`.

Mode caps on concept-set distance: conservative ≤ low, balanced ≤ moderate, exploratory ≤ high (primary-concept preservation is enforced separately by operator contracts). Exceeding the cap gives `REVIEW_REQUIRED`.

## Duplicates and diversity

- Surface duplicate: word-sequence similarity ≥ 0.8. Near-verbatim source copy: ≥ 0.85 against any source question → `FAIL`.
- Structural duplicate: identical signature (concept set, step-type sequence, representations, answer type, given values).
- Diversity selection: greedy farthest-point; ordering distance = mean of the five structural distances + 0.5 × surface distance, ties by ID. This combination is only used to order candidates and is never reported as a metric.
