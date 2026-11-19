# Installing the ExamDNA Skill

The distributable is `examdna-v0.1.0.zip` (built by `python -m examdna.cli package` into `dist/`, checksum in `dist/SHA256SUMS.txt`). It contains one folder, `examdna/`, with `SKILL.md`, `references/`, `assets/`, `schemas/` and `scripts/` (launcher + vendored engine). Requirements: Python 3.9+ available to the agent. No pip installs, API keys or servers.

## Claude Code

Claude Code discovers Skills in `.claude/skills/<name>/SKILL.md` folders.

**Personal Skill** (available in every project):

```powershell
Expand-Archive examdna-v0.1.0.zip -DestinationPath "$HOME\.claude\skills"
```

macOS / Linux: `unzip examdna-v0.1.0.zip -d ~/.claude/skills`

**Project Skill** (shared with collaborators through git): unzip into `<project>/.claude/skills/` instead.

Check: `~/.claude/skills/examdna/SKILL.md` exists. Restart Claude Code (or start a new session) and ask something like "analyze these past papers". The development checkout of this repository already contains a project Skill at `.claude/skills/examdna/` that runs the engine from the repository.

## Claude.ai

1. Make sure code execution / file creation is enabled for your account (Settings → Capabilities).
2. In Settings → Capabilities → Skills, upload `examdna-v0.1.0.zip` as a custom Skill and enable it.
3. In a new chat, upload papers and ask for an exam.

Plan availability, menu names and limits are set by Anthropic and change over time — follow the current help-center article "Using Skills in Claude" if the steps above differ. Skills are uploaded from the web or desktop app; mobile apps can use Skills that are enabled on the account where the client supports them. The engine then runs in Anthropic's hosted sandbox (not on your device).

## Other Agent Skills hosts

Any host that loads a folder with a `SKILL.md` (YAML frontmatter `name`, `description`) and lets the agent run Python should work: unzip the folder where that host expects Skills. Not tested by the authors.

## Developers

```powershell
git clone <repository-url>
cd ExamDNA
python -m unittest discover -s tests -t .
python tools/run_demo.py
python -m examdna.cli package
```

Optional extras: `pip install -e .[pdf]` (PDF text extraction), `pip install weasyprint` (PDF export from HTML; has system dependencies).
