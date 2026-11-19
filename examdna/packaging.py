"""Build and verify the self-contained Skill archive.

Layout of ``examdna-v<version>.zip``::

    examdna/
      SKILL.md
      LICENSE.txt
      references/*.md
      assets/*
      schemas/*.schema.json          (copied from the package)
      scripts/examdna_cli.py         (entry point)
      scripts/examdna/...            (vendored copy of this package)

Archives are deterministic: sorted entries, fixed timestamps, fixed
permissions — rebuilding the same sources yields the same SHA-256.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

from . import __version__

EXCLUDE_DIRS = {"__pycache__", ".git", ".venv", "venv", "env", ".mypy_cache", ".pytest_cache", ".idea", ".vscode", "node_modules", "dist", "build"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".log", ".tmp"}
EXCLUDE_NAMES = {".env", ".DS_Store", "Thumbs.db", "credentials.json", "secrets.json", ".coverage"}
FORBIDDEN_PATTERNS = [re.compile(p) for p in (r"(^|/)\.git(/|$)", r"(^|/)__pycache__(/|$)", r"\.pyc$", r"(^|/)\.env$", r"(^|/)(venv|\.venv)(/|$)")]
SECRET_PATTERNS = [re.compile(p) for p in (r"sk-ant-[A-Za-z0-9_-]{20,}", r"sk-[A-Za-z0-9]{32,}", r"AKIA[0-9A-Z]{16}", r"-----BEGIN (RSA |EC )?PRIVATE KEY-----", r"ghp_[A-Za-z0-9]{30,}")]
MAX_ARCHIVE_BYTES = 30 * 1024 * 1024
MAX_ENTRY_BYTES = 5 * 1024 * 1024
FIXED_TIME = (2024, 1, 1, 0, 0, 0)
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")


class PackageError(Exception):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if path.is_file() and path.suffix not in EXCLUDE_SUFFIXES and path.name not in EXCLUDE_NAMES:
            yield path, rel


def stage_skill(root: Path, staging: Path) -> Path:
    skill_src = root / ".claude" / "skills" / "examdna"
    pkg_src = root / "examdna"
    if not (skill_src / "SKILL.md").is_file():
        raise PackageError(f"SKILL.md not found in {skill_src}")
    target = staging / "examdna"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for path, rel in _iter_files(skill_src):
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    for path, rel in _iter_files(pkg_src):
        dest = target / "scripts" / "examdna" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    for path in sorted((pkg_src / "schemas").glob("*.schema.json")):
        dest = target / "schemas" / path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    lic = root / "LICENSE"
    if lic.is_file():
        shutil.copyfile(lic, target / "LICENSE.txt")
    return target


def _zip_dir(src: Path, archive: Path) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(p for p in src.rglob("*") if p.is_file()):
            arc = path.relative_to(src.parent).as_posix()
            info = zipfile.ZipInfo(arc, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            data = path.read_bytes().replace(b"\r\n", b"\n") if path.suffix in {".py", ".md", ".json", ".txt"} else path.read_bytes()
            zf.writestr(info, data)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_frontmatter(text: str) -> Dict[str, str]:
    if not text.startswith("---"):
        raise PackageError("SKILL.md must start with YAML frontmatter ('---')")
    end = text.find("\n---", 3)
    if end == -1:
        raise PackageError("SKILL.md frontmatter is not closed")
    fm: Dict[str, str] = {}
    current = None
    for line in text[3:end].strip("\n").splitlines():
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if m:
            current = m.group(1)
            fm[current] = m.group(2).strip().strip('"').strip("'")
        elif current and line.startswith((" ", "\t")):
            fm[current] = (fm[current] + " " + line.strip()).strip()
        else:
            raise PackageError(f"cannot parse frontmatter line: {line!r}")
    return fm


def verify_archive(archive: Path, run_smoke_test: bool = True) -> Dict[str, object]:
    """Structural verification of a Skill zip. Raises PackageError on failure."""
    problems: List[str] = []
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        problems.append("archive too large")
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        for name in names:
            if name.startswith("/") or "\\" in name or ".." in Path(name).parts or re.match(r"^[A-Za-z]:", name):
                problems.append(f"unsafe path in archive: {name}")
            if not name.startswith("examdna/"):
                problems.append(f"entry outside top-level 'examdna/' folder: {name}")
            if any(p.search(name) for p in FORBIDDEN_PATTERNS):
                problems.append(f"forbidden entry: {name}")
        for info in zf.infolist():
            if info.file_size > MAX_ENTRY_BYTES:
                problems.append(f"entry too large: {info.filename}")
            if (info.external_attr >> 16) & 0o170000 == stat.S_IFLNK:
                problems.append(f"symlink in archive: {info.filename}")
        if "examdna/SKILL.md" not in names:
            raise PackageError("examdna/SKILL.md missing from archive")
        skill_text = zf.read("examdna/SKILL.md").decode("utf-8")
        fm = parse_frontmatter(skill_text)
        if not NAME_RE.match(fm.get("name", "")):
            problems.append("frontmatter 'name' must be lowercase letters, digits and hyphens (max 64)")
        if fm.get("name") != "examdna":
            problems.append("frontmatter name must be 'examdna' (matching the folder name)")
        desc = fm.get("description", "")
        if not desc or len(desc) > 1024:
            problems.append("frontmatter 'description' must be 1..1024 characters")
        if "<" in desc or ">" in desc:
            problems.append("description must not contain angle brackets")
        referenced = set(re.findall(r"(?<![\w/])((?:scripts|references|assets|schemas)/[A-Za-z0-9_./-]+\.(?:md|py|json|html|css))", skill_text))
        for ref in sorted(referenced):
            if f"examdna/{ref}" not in names:
                problems.append(f"SKILL.md references missing file: {ref}")
        for name in names:
            if name.endswith((".py", ".md", ".json", ".txt")):
                text = zf.read(name).decode("utf-8", errors="replace")
                for pat in SECRET_PATTERNS:
                    if pat.search(text):
                        problems.append(f"possible secret in {name}")
                if re.search(r"[A-Za-z]:\\\\Users\\\\|/Users/[a-z]+/|/home/[a-z]+/", text) and not name.endswith("packaging.py"):
                    problems.append(f"machine-specific absolute path in {name}")
        required = ["examdna/scripts/examdna_cli.py", "examdna/scripts/examdna/__init__.py", "examdna/scripts/examdna/schemas/question.schema.json"]
        for r in required:
            if r not in names:
                problems.append(f"required file missing: {r}")
        smoke = None
        if run_smoke_test and not problems:
            with tempfile.TemporaryDirectory() as tmp:
                zf.extractall(tmp)
                cli = Path(tmp) / "examdna" / "scripts" / "examdna_cli.py"
                proc = subprocess.run([sys.executable, "-I", str(cli), "--version"], capture_output=True, text=True, timeout=60, cwd=tmp)
                smoke = {"returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()[-500:]}
                if proc.returncode != 0 or __version__ not in proc.stdout:
                    problems.append(f"smoke test failed: {smoke}")
                proc2 = subprocess.run([sys.executable, "-I", str(cli), "operators", "--json"], capture_output=True, text=True, timeout=60, cwd=tmp)
                if proc2.returncode != 0 or '"reverse"' not in proc2.stdout:
                    problems.append("smoke test 'operators' failed")
    if problems:
        raise PackageError("; ".join(problems))
    return {"archive": str(archive), "entries": len(names), "frontmatter": fm, "smoke_test": smoke, "sha256": sha256(archive)}


def build(out_dir: Optional[Path] = None, root: Optional[Path] = None, verify: bool = True) -> Dict[str, object]:
    root = root or repo_root()
    out_dir = Path(out_dir or (root / "dist"))
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        staged = stage_skill(root, Path(tmp))
        archive = out_dir / f"examdna-v{__version__}.zip"
        _zip_dir(staged, archive)
    result: Dict[str, object] = {"archive": str(archive), "sha256": sha256(archive)}
    if verify:
        result["verification"] = verify_archive(archive)
    sums = out_dir / "SHA256SUMS.txt"
    sums.write_bytes(f"{result['sha256']}  {archive.name}\n".encode("utf-8"))
    result["checksums"] = str(sums)
    return result
