# Contributing to ExamDNA

Thanks for helping. ExamDNA values working, tested, honestly documented code over feature count.

## Setup

```powershell
git clone <repository-url>
cd ExamDNA
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -e .[dev]
python -m unittest discover -s tests -t .    # or: pytest
python tools/run_demo.py
```

The core must keep working with the **Python 3.9+ standard library only**. Optional dependencies must be imported lazily inside the function that needs them, with a clear fallback message.

## Conventions

- Deterministic code: no unseeded randomness, no wall-clock values in outputs, sorted iteration where order matters.
- Never present a heuristic or model judgement as verified. New checks must label their `method`.
- Read and write files as UTF-8 explicitly. Treat every input as untrusted (size limits, no `eval`, no shell).
- Schema keys and identifiers in English; user-facing labels go through `examdna/reporting/i18n.py`.
- Keep `SKILL.md` short; detailed material belongs in `.claude/skills/examdna/references/`.
- Example data must be original. Never commit real past papers, textbooks or mark schemes.

## Tests

Every change needs tests. Unit tests live in `tests/unit/`, end-to-end workflows in `tests/integration/`. If you change the demo pipeline, run `python tools/run_demo.py` and commit the regenerated `examples/expected_outputs/` (the output is deterministic, so diffs show real changes).

## Adding a mutation operator

See [docs/mutation-operators.md](docs/mutation-operators.md#adding-an-operator): register a contract, add a deterministic parameter builder, add property checks if needed, add tests with one valid and one invalid candidate, document it in both docs and the Skill reference.

## Modifying schemas

1. Edit `examdna/schemas/*.schema.json`; keep `additionalProperties: false` where it is set.
2. Additive optional fields → patch version (`0.1.x`); renames/removals → minor version with a migration note in `CHANGELOG.md`.
3. Update the builder/normalizer that produces the object, the Skill references that describe it, and the tests.

## Pull requests

- One topic per PR; describe what changed and how you tested it.
- CI must pass on all platforms.
- Update `CHANGELOG.md` under "Unreleased".

## Reporting bugs

Open an issue with: ExamDNA version, OS, Python version, the command, the full error, and a *minimal synthetic* input that reproduces it. Do not attach real exam papers or personal data. Security problems: see [SECURITY.md](SECURITY.md).
