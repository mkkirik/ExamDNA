# Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `examdna: could not find the examdna package` | The launcher is outside both a Skill zip layout and a repository checkout. Re-extract the zip so `scripts/examdna/__init__.py` exists next to `scripts/examdna_cli.py`. |
| `Python 3.9 or newer is required` | Install a current Python, or call `python3`. |
| `malformed JSON at line …` | Fix the JSON (no trailing commas, double quotes, no NaN). Duplicate keys are rejected on purpose. |
| `conflicting question identifiers` | Two questions share an ID (possibly across merged files). Rename one. |
| `annotations reference unknown question ids` | Annotation keys must match `bank.json` IDs exactly. |
| Planner skips a question: `genome is minimal` | Add `primary_concept` and reasoning steps to its annotation. |
| Candidate `FAIL preserve:…` | The candidate changed something the spec preserves. Copy the parent's genome parts verbatim where preservation is required (e.g. same step types, same constraint wording, same `answer_type`). |
| Candidate `FAIL source_copy` / `novelty` | Wording too close to a source question; rewrite rather than editing a few words. |
| Candidate `FAIL recompute` / `final_answer_matches` | The claimed or written answer does not match the expression with the stated values. |
| `units NOT_VERIFIED: unit of 'x' is unknown` | Give the given a unit (use `"1"` for dimensionless) or a supported SI unit string. |
| `REVIEW_REQUIRED judgement:target_skill` | Supply `invariant_judgements` for every name in the spec's `required_judgements`. |
| Compile exit code 2 | Read `compile_diagnosis.json`; it lists reachable mark totals, missing topics/types and suggestions. |
| `PDF text extraction needs the optional 'pypdf'` | `pip install pypdf`, or let the agent read the PDF and write JSON. |
| Turkish characters garbled in your own scripts on Windows | Open files with `encoding="utf-8"`. |
