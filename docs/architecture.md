# Architecture

## Layers

| Layer | Who | Responsibilities |
| --- | --- | --- |
| 1. Agent orchestration | Claude, guided by `SKILL.md` | Read documents (incl. PDFs/scans via the host's own capabilities), extract questions, tag topics/cognitive level, annotate genomes, write candidate questions from specs, make explicit semantic judgements, talk to the user |
| 2. Deterministic engine | `examdna` Python package | Schemas, normalization, statistics, genome assembly, mutation planning, numeric/unit/invariant validation, duplicate detection, lineage, exam compilation |
| 3. Presentation | `examdna.reporting` | Student paper (Markdown + print-ready HTML), answer key, marking guide, reports, JSON exports |

A Python script cannot call the model that is running the Skill, and ExamDNA never calls any model API. The layers communicate only through JSON files validated against schemas in `examdna/schemas/`. Every semantic field carries provenance (`explicit`, `inferred`, `calculated`, `unverified`), and every validation check is labelled `deterministic`, `model_assisted` or `human`.

## Data flow

```
bank.json ──(+annotations.json)──► genomes.json ──► exam_dna.json
     │                                  │
     └──────────────► mutation_plan.json ◄┘          (Stage A: deterministic)
                             │
                     candidates.json                  (Stage B: agent writes)
                             │
           validation_report.json + validated_pool.json
                             │
              compile_config.json ──► exam.json ──► output/*.md, *.html, reports/*.md
```

## Package layout

```
examdna/
  models/        constants (vocabularies), mini JSON-Schema validator
  schemas/       question, question_bank, genome, mutation_spec, mutation_plan, candidate, compile_config, exam_dna
  extraction/    loaders (JSON, CSV, Markdown/text parser, optional PDF) and normalization
  fingerprint/   Exam DNA analyzer, heuristic difficulty model
  genome/        genome builder, reasoning-graph analysis, genome comparison
  mutation/      operator registry, planner, property checks, distance, diversity, lineage
  validation/    safe expression evaluator, SI units, checks, pipeline
  compiler/      constraint-aware exam assembly
  reporting/     renderers, reports, en/tr labels
  evaluation.py  baseline vs ExamDNA observable-property comparison
  workflow.py    prepare / finish workspace orchestration
  packaging.py   deterministic Skill zip builder and verifier
  cli.py         command-line interface
```

## Skill packaging decision

The repository keeps one copy of the engine (`examdna/`). The development Skill (`.claude/skills/examdna/`) contains only `SKILL.md`, references, assets and a 30-line launcher, `scripts/examdna_cli.py`, which imports the engine from a vendored copy next to it or — in a development checkout — from the repository root. `examdna package` builds the distributable zip by vendoring the package into `scripts/examdna/` and copying schemas to `schemas/`, so the archive is self-contained and has no duplicated sources in git.

## Key decisions

- **Standard library only** for portability (Claude.ai sandbox, locked-down school machines, Windows without compilers). Optional: `pypdf` (PDF text), `weasyprint` (PDF export).
- **Own JSON-Schema subset validator** instead of `jsonschema` to avoid a dependency; tested against the keywords the schemas use.
- **AST-whitelisted evaluator** with exact `fractions` arithmetic where possible; never `eval`.
- **Exact-sum branch-and-bound** rather than greedy selection, because hard mark totals are the most common requirement; a node budget bounds runtime and the result states whether the search was exhaustive.
- **Deterministic everything** (seeded RNG derived from content hashes, sorted iteration, fixed zip timestamps) so plans, exams and archives are byte-for-byte reproducible.
