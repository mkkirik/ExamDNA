"""Safe file input/output.

All user-supplied files are treated as untrusted data. Readers enforce size
limits, allowed suffixes, strict JSON (no NaN/Infinity, no duplicate keys) and
a maximum nesting depth. Nothing read here is ever executed or evaluated.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Optional

MAX_INPUT_BYTES = 10 * 1024 * 1024  # 10 MiB per input file
MAX_JSON_DEPTH = 64
TEXT_SUFFIXES = {".md", ".markdown", ".txt"}
DATA_SUFFIXES = {".json", ".csv"}
DEFAULT_ALLOWED = TEXT_SUFFIXES | DATA_SUFFIXES

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class InputError(ValueError):
    """Raised when an input file or structure is rejected."""


def _check_file(path: Path, allowed_suffixes: Optional[Iterable[str]], max_bytes: int) -> Path:
    try:
        resolved = Path(path).expanduser().resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise InputError(f"Input file not found: {path}") from exc
    if not resolved.is_file():
        raise InputError(f"Input path is not a regular file: {path}")
    if allowed_suffixes is not None:
        allowed = {s.lower() for s in allowed_suffixes}
        if resolved.suffix.lower() not in allowed:
            raise InputError(
                f"Unsupported file type '{resolved.suffix or '(none)'}' for {resolved.name}; "
                f"expected one of: {', '.join(sorted(allowed))}"
            )
    size = resolved.stat().st_size
    if size > max_bytes:
        raise InputError(f"Input file {resolved.name} is {size} bytes; limit is {max_bytes} bytes")
    return resolved


def read_text_file(
    path: os.PathLike | str,
    allowed_suffixes: Optional[Iterable[str]] = DEFAULT_ALLOWED,
    max_bytes: int = MAX_INPUT_BYTES,
) -> str:
    resolved = _check_file(Path(path), allowed_suffixes, max_bytes)
    raw = resolved.read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InputError(f"{resolved.name} is not valid UTF-8 text") from exc


def _reject_constant(name: str) -> Any:
    raise InputError(f"Non-standard JSON constant '{name}' is not allowed")


def _no_duplicate_keys(pairs: list) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"Duplicate JSON key '{key}'")
        result[key] = value
    return result


def _depth(obj: Any, limit: int) -> None:
    stack = [(obj, 1)]
    while stack:
        item, depth = stack.pop()
        if depth > limit:
            raise InputError(f"JSON nesting deeper than {limit} levels")
        if isinstance(item, dict):
            stack.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            stack.extend((v, depth + 1) for v in item)


def parse_json_text(text: str, source: str = "<string>") -> Any:
    try:
        data = json.loads(text, parse_constant=_reject_constant, object_pairs_hook=_no_duplicate_keys)
    except InputError as exc:
        raise InputError(f"{source}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"{source}: malformed JSON at line {exc.lineno} column {exc.colno}: {exc.msg}") from exc
    _depth(data, MAX_JSON_DEPTH)
    return data


def read_json_file(path: os.PathLike | str, max_bytes: int = MAX_INPUT_BYTES) -> Any:
    text = read_text_file(path, allowed_suffixes={".json"}, max_bytes=max_bytes)
    return parse_json_text(text, source=Path(path).name)


def write_json(path: os.PathLike | str, data: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)
    target.write_bytes((text + "\n").encode("utf-8"))  # LF on every OS; Path.write_text(newline=) needs 3.10+
    return target


def write_text(path: os.PathLike | str, text: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    target.write_bytes(text.encode("utf-8"))
    return target


def safe_filename(name: str, default: str = "file") -> str:
    """Reduce an arbitrary string to a portable file name (no separators)."""
    cleaned = _SAFE_NAME.sub("_", name).strip("._")
    cleaned = cleaned[:100]
    if not cleaned or cleaned in {".", ".."}:
        return default
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if cleaned.split(".")[0].upper() in reserved:
        cleaned = "_" + cleaned
    return cleaned


def safe_join(base: os.PathLike | str, *parts: str) -> Path:
    """Join path parts under ``base`` and refuse anything that escapes it."""
    base_path = Path(base).resolve()
    candidate = base_path.joinpath(*parts).resolve()
    try:
        candidate.relative_to(base_path)
    except ValueError as exc:
        raise InputError(f"Path escapes the workspace: {'/'.join(parts)}") from exc
    return candidate
