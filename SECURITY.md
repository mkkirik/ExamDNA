# Security policy

## Reporting a vulnerability

Please report security issues privately through the repository's **Security → Report a vulnerability** (GitHub private advisory) rather than a public issue. Include a minimal synthetic reproduction. We aim to acknowledge reports within 7 days.

## Threat model

ExamDNA processes untrusted documents (exam papers, notes) and untrusted agent-written JSON.

| Threat | Mitigation |
| --- | --- |
| Prompt injection inside uploaded documents | `SKILL.md` instructs the agent to treat documents as data; the engine flags instruction-like text (`security_flags`) and marks such questions `needs_review`. Pattern detection is a tripwire, not a guarantee. |
| Code execution through answer expressions | AST whitelist evaluator; no `eval`/`exec`; bounded exponent and length. |
| Malformed or hostile JSON | Strict parser (no NaN/Infinity, duplicate keys rejected), depth ≤ 64, 10 MiB file limit, schema validation with `additionalProperties: false`. |
| Path traversal / unsafe file names | IDs restricted to a safe pattern; `safe_join` and `safe_filename` helpers; outputs written only to user-chosen paths. |
| Unsafe archive contents | `verify-package` rejects absolute paths, `..`, entries outside `examdna/`, symlinks, `.git`, caches, oversized entries, likely secrets and machine-specific paths. |
| Resource exhaustion | Question-count, file-size and solver node limits. |
| Secret leakage | No API keys are used or stored; `.gitignore` excludes `.env`, keys and credentials; packaging scans for common key formats. |

## Privacy

No telemetry, analytics or network calls. In Claude Code the engine runs on your machine. In Claude.ai the files you upload and the engine run in Anthropic's hosted environment under Anthropic's terms — that is not local processing. Do not commit real student data or copyrighted papers to a public fork.
