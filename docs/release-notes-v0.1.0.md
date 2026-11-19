# ExamDNA v0.1.0 — release notes

First public release of ExamDNA: an Agent Skill and dependency-free Python engine that reverse-engineers exam structure, plans controlled question mutations, validates generated questions deterministically and compiles new practice exams under hard constraints.

## Artifacts

| File | Purpose |
| --- | --- |
| `examdna-v0.1.0.zip` | Self-contained Skill (single `examdna/` folder) for Claude Code (`~/.claude/skills/` or `<project>/.claude/skills/`) and Claude.ai custom Skill upload |
| `SHA256SUMS.txt` | SHA-256 checksum of the zip (the archive is built deterministically) |

## Highlights

- Exam DNA blueprint with evidence IDs and explicit evidence levels.
- Question genome schema 0.1.0 with reasoning graphs and per-field provenance.
- Nine mutation operators with contracts; reproducible mutation plans; multi-generation lineage.
- Validation: exact recomputation, SI dimensional analysis, invariants, copy detection, ambiguity flags; model-assisted checks are labelled.
- Exact-sum exam compiler with infeasibility diagnosis.
- Print-ready HTML/Markdown exams, separate answer key and marking guide, English/Turkish labels.

## Verified

- 110 automated tests passing in GitHub Actions on Linux (Python 3.10–3.13), macOS and Windows (Python 3.9–3.13), and locally on Windows 11 with Python 3.9 and 3.11–3.14 (88 % line coverage of the package).
- Demo outputs reproduce byte-for-byte in CI on every platform.
- Skill archive verified (structure, frontmatter, referenced files, no secrets/caches/absolute paths) and smoke-tested from a fresh extraction; the full workflow run from the extracted archive reproduces the demo exam exactly.

## Not yet verified

- Python 3.9 on Linux (no runner build available; passes on Windows and macOS).
- Claude.ai upload and mobile usage.
- Optional PDF extraction (`pypdf`) and PDF export (`weasyprint`).

## Limitations

Heuristic difficulty (not calibrated); no symbolic maths; non-numeric answers need human review; semantic judgements are model-assisted; lexical copy detection cannot guarantee legal originality. ExamDNA does not predict real exams and is not affiliated with any examination board.
