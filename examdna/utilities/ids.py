"""Identifier helpers. IDs are ASCII, portable and safe to use in file names."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any

ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"
_ID_RE = re.compile(ID_PATTERN)


def is_valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ID_RE.match(value)) and ".." not in value


# Letters that do not decompose to ASCII under NFKD (e.g. Turkish dotless ı).
_TRANSLIT = str.maketrans({"ı": "i", "İ": "I", "ß": "ss", "ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE", "đ": "d", "ł": "l", "Ł": "L"})


def slugify(text: str, max_len: int = 40) -> str:
    normalized = unicodedata.normalize("NFKD", str(text).translate(_TRANSLIT)).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", normalized).strip("-").lower()
    return slug[:max_len].strip("-") or "x"


def digest(*parts: Any, length: int = 10) -> str:
    payload = json.dumps(parts, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any, length: int = 10) -> str:
    """Deterministic ID derived from content, e.g. ``spec-1a2b3c4d5e``."""
    return f"{slugify(prefix, 20)}-{digest(*parts, length=length)}"


def seed_for(*parts: Any) -> int:
    """Derive a reproducible integer seed from arbitrary parts."""
    return int(digest(*parts, length=12), 16)
