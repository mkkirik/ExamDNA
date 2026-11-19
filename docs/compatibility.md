# Compatibility status (v0.1.0)

| Environment | Status | Evidence |
| --- | --- | --- |
| Windows 11, Python 3.11 / 3.12 / 3.13 / 3.14 | **Tested** — full test suite passes | Local runs during development |
| Python 3.9, 3.10 | Expected to work (no newer syntax used); **pending CI** | `.github/workflows/tests.yml` |
| Ubuntu (Linux), macOS | **Pending CI** — not run locally | `.github/workflows/tests.yml` matrix |
| Claude Code — project Skill from this repository | Launcher and CLI tested via subprocess; end-to-end agent session **not recorded** | `tests/integration/test_workflows.py::test_module_invocation` |
| Skill zip extracted to a fresh folder | **Tested** — smoke test runs `--version` and `operators` from the extracted archive with `python -I` | `examdna verify-package` / packaging test |
| Claude.ai custom Skill upload | **Not tested** by the authors | — |
| Claude mobile apps | **Not tested** | — |
| PDF text extraction (`pypdf`) | Code path present, **not tested** (optional dependency not installed in CI) | — |
| PDF export (`weasyprint`) | Code path present, **not tested** | — |

Results marked "pending CI" become verified only after the GitHub Actions workflow has actually run on those platforms.

## Known platform notes

- The engine always reads and writes UTF-8 explicitly, so Windows code pages (e.g. cp1254 for Turkish locales) do not affect it. Your own ad-hoc scripts should do the same.
- Use `python3` on systems where `python` is not Python 3.
- Paths are handled with `pathlib`; both `/` and `\` work on Windows.
