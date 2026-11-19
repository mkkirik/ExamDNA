# CLI reference

Invoke as `examdna …` (after `pip install -e .`), `python -m examdna.cli …` from the repository root, or `python <skill>/scripts/examdna_cli.py …` inside the Skill. All paths may be relative or absolute and use the host OS's conventions. Exit codes: `0` ok, `1` input/validation error (message on stderr), `2` compilation infeasible.

The CLI never generates question text. Agent-assisted steps (extraction, annotation, candidates) produce JSON that these commands consume.

| Command | Purpose | Key arguments |
| --- | --- | --- |
| `ingest INPUT… --out BANK` | Normalize JSON / CSV / Markdown / text (PDF with optional `pypdf`) into a bank; merges several inputs; rejects conflicting IDs | `--subject`, `--document` |
| `extract-text FILE --out TXT` | PDF (optional `pypdf`) or text → plain text | |
| `genome --bank B [--annotations A] --out G` | Build genomes | exit 1 if any genome has errors |
| `analyze --bank B [--genomes G] --out DNA [--report MD]` | Exam DNA profile and report | |
| `compare --genomes G --a ID --b ID [--bank B]` | Dimension-by-dimension genome comparison | |
| `operators [--json]` | Operator contracts | |
| `mutation-plan --bank B --genomes G --out PLAN` | Deterministic specs | `--mode conservative/balanced/exploratory`, `--operators a,b`, `--questions id,id`, `--per-question N`, `--seed N`, `--direction up/down`, `--variants N --question ID` |
| `validate --bank B --candidates C --plan P --genomes G --out R` | Validate candidates | `--pool OUT` (accepted questions + genomes), `--summary MD` |
| `validate --bank B --out R` | Validate an existing bank on its own | `--pool OUT` writes the bank with states |
| `compile --pool P --config C --out EXAM` | Assemble an exam | `--dna`, `--genomes`, `--seed`, `--diagnosis FILE` |
| `render --exam EXAM --out-dir DIR` | exam.md, exam.html, answer_key.md, marking_guide.md | `--lang en/tr`, `--pdf` (optional `weasyprint`) |
| `report dna/validation/lineage/compare --out MD` | Markdown reports | `--dna`, `--report`, `--bank`, `--pool`, `--exam` |
| `lineage --bank B [--pool P] [--out JSON]` | Print the lineage tree | exit 1 on lineage errors |
| `evaluate --baseline B --exam E --config C --out JSON` | Observable-property comparison | `--bank`, `--validation`, `--markdown` |
| `prepare --workspace DIR` | bank.json (+annotations.json) → genomes, DNA, plan, DNA report | same options as `mutation-plan` |
| `finish --workspace DIR` | candidates.json + compile_config.json → validation, pool, exam, outputs, reports | `--output-dir`, `--seed` |
| `package [--out DIR]` | Build and verify the Skill zip + SHA256SUMS | `--no-verify` |
| `verify-package ZIP` | Structural verification + smoke test of a Skill zip | |
| `schema NAME` / `schema list` | Print a JSON schema | |

## Workspace files

`bank.json`, `annotations.json`, `genomes.json`, `exam_dna.json`, `mutation_plan.json`, `candidates.json`, `compile_config.json`, `validation_report.json`, `validated_pool.json`, `exam.json`, `compile_diagnosis.json`, `output/`, `reports/`.
