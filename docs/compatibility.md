# Compatibility status (v0.1.0)

| Environment | Status | Evidence |
| --- | --- | --- |
| Windows 11, Python 3.9 / 3.11 / 3.12 / 3.13 / 3.14 | **Tested** — full test suite passes | Local runs during development |
| GitHub Actions: Windows, macOS — Python 3.9–3.13 | **Tested** — tests, demo reproducibility and package build pass | CI run 44637038707 |
| GitHub Actions: Ubuntu — Python 3.10–3.13 | **Tested** — tests, demo reproducibility and package build pass | CI run 44637038707 |
| Ubuntu — Python 3.9 | Not run in CI: `setup-python` provides no 3.9 build for the current Ubuntu runner image (3.9 is end-of-life). The same code passes 3.9 on Windows and macOS. | — |
| Claude Code — project Skill from this repository | Launcher and CLI tested via subprocess; end-to-end agent session **not recorded** | `tests/integration/test_workflows.py::test_module_invocation` |
| Skill zip extracted to a fresh folder | **Tested** — smoke test runs `--version` and `operators` from the extracted archive with `python -I` | `examdna verify-package` / packaging test |
| Claude.ai custom Skill upload | **Not tested** by the authors | — |
| Claude mobile apps | **Not tested** | — |
| PDF text extraction (`pypdf`) | Code path present, **not tested** (optional dependency not installed in CI) | — |
| PDF export (`weasyprint`) | Code path present, **not tested** | — |

CI results refer to the workflow in `.github/workflows/tests.yml` on the `main` branch; see the repository's Actions tab for the latest runs.

## Known platform notes

- The engine always reads and writes UTF-8 explicitly, so Windows code pages (e.g. cp1254 for Turkish locales) do not affect it. Your own ad-hoc scripts should do the same.
- Use `python3` on systems where `python` is not Python 3.
- Paths are handled with `pathlib`; both `/` and `\` work on Windows.
