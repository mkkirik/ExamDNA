"""Loaders for supported source formats.

* ``.json``  — question bank (list or ``{"questions": [...]}``)
* ``.csv``   — one question per row; list fields separated by ``;``
* ``.md`` / ``.txt`` — a deterministic heuristic parser for plainly formatted
  exams (``Section A``, ``1.``, ``(a)``, ``[3 marks]``). It only splits text;
  it does not guess topics. Records it produces are ``agent_extracted`` style
  with ``medium``/``low`` confidence and should be enriched by the agent.
* ``.pdf`` — text extraction only if the optional ``pypdf`` package is
  installed. Otherwise the agent should read the PDF itself and write a JSON
  bank (see references/extraction-guide.md).
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utilities.io import InputError, MAX_INPUT_BYTES, parse_json_text, read_text_file
from .normalize import normalize_bank

_SECTION_RE = re.compile(r"^\s*(?:#+\s*)?(?:section|bölüm|part)\s+([A-Z0-9]{1,3})\b[:.\-—]?\s*(.*)$", re.IGNORECASE)
_QUESTION_RE = re.compile(r"^\s*(?:#+\s*)?(?:q(?:uestion)?\.?\s*|soru\s*)?(\d{1,3})\s*[.)]\s+(.*)$", re.IGNORECASE)
_PART_RE = re.compile(r"^\s*\(([a-h]|i{1,3}|iv|v|vi{0,3})\)\s+(.*)$")
_MARKS_RE = re.compile(r"[\[(]\s*(\d{1,3})\s*(?:marks?|mark|pts?|points?|puan)?\s*[\])]\s*$", re.IGNORECASE)
_HEADER_KV = re.compile(r"^\s*(subject|topic|paper|title)\s*:\s*(.+)$", re.IGNORECASE)


def _strip_marks(line: str):
    m = _MARKS_RE.search(line)
    if not m:
        return line.strip(), None
    return line[: m.start()].strip(), int(m.group(1))


def parse_text_exam(text: str, document: str) -> Dict[str, Any]:
    """Split a plainly formatted exam into raw question records."""
    records: List[Dict[str, Any]] = []
    section: Optional[str] = None
    subject: Optional[str] = None
    current: Optional[Dict[str, Any]] = None
    current_part: Optional[Dict[str, Any]] = None

    def flush():
        nonlocal current, current_part
        if current is not None:
            current["text"] = "\n".join(current.pop("_lines")).strip()
            for p in current["parts"]:
                p["text"] = "\n".join(p.pop("_lines")).strip()
            if not current["parts"]:
                current.pop("parts")
            if current["text"] or current.get("parts"):
                if not current["text"]:
                    current["text"] = "(see parts)"
                records.append(current)
        current, current_part = None, None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        kv = _HEADER_KV.match(line)
        if kv and current is None:
            if kv.group(1).lower() == "subject":
                subject = kv.group(2).strip()
            continue
        sec = _SECTION_RE.match(line)
        if sec:
            flush()
            section = sec.group(1).upper()
            continue
        q = _QUESTION_RE.match(line)
        if q:
            flush()
            body, marks = _strip_marks(q.group(2))
            current = {
                "id": None,
                "number": int(q.group(1)),
                "section": section,
                "marks": marks,
                "parts": [],
                "_lines": [body] if body else [],
                "extraction_confidence": "medium",
                "evidence": [{"document": document, "page": None, "quote": body[:200] if body else None}],
            }
            current_part = None
            continue
        p = _PART_RE.match(line)
        if p and current is not None:
            body, marks = _strip_marks(p.group(2))
            current_part = {"label": p.group(1), "marks": marks, "_lines": [body]}
            current["parts"].append(current_part)
            continue
        if current is None:
            continue
        body, marks = _strip_marks(line)
        target = current_part if current_part is not None else current
        if body:
            target["_lines"].append(body)
        if marks is not None and target.get("marks") is None:
            target["marks"] = marks
    flush()

    stem = re.sub(r"[^A-Za-z0-9]+", "-", Path(document).stem).strip("-").lower() or "doc"
    for rec in records:
        number = rec.pop("number")
        rec["id"] = f"{stem}-q{number}" if not rec.get("section") else f"{stem}-{rec['section'].lower()}{number}"
        if rec.get("parts") and rec.get("marks") is not None:
            # marks found on the stem line *and* on parts: keep stem marks, normalizer checks the sum
            pass
        if any(p.get("marks") is None for p in rec.get("parts", [])) or (rec.get("marks") is None and not rec.get("parts")):
            rec["extraction_confidence"] = "low"
    return {"default_document": document, "subject": subject, "questions": records}


def _csv_records(text: str) -> List[Dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "text" not in [f.strip() for f in reader.fieldnames]:
        raise InputError("CSV must have a header row that includes a 'text' column")
    rows = []
    for row in reader:
        rec: Dict[str, Any] = {}
        for key, value in row.items():
            if key is None:
                raise InputError("CSV row has more cells than header columns")
            key = key.strip()
            value = (value or "").strip()
            if value == "":
                continue
            if key in ("learning_objectives",):
                rec[key] = [v.strip() for v in value.split(";") if v.strip()]
            elif key == "final_answer":
                rec.setdefault("marking", {})["final_answer"] = value
            else:
                rec[key] = value
        rows.append(rec)
    return rows


def load_source(
    path: str | Path,
    *,
    subject: Optional[str] = None,
    document: Optional[str] = None,
    max_bytes: int = MAX_INPUT_BYTES,
) -> Dict[str, Any]:
    """Load and normalize a single source file into a question bank."""
    p = Path(path)
    suffix = p.suffix.lower()
    doc_name = document or p.name
    if suffix == ".pdf":
        text = extract_pdf_text(p, max_bytes=max_bytes)
        raw = parse_text_exam(text, doc_name)
        return normalize_bank(raw, default_subject=subject, origin="agent_extracted", default_provenance="explicit")
    if suffix == ".json":
        raw = parse_json_text(read_text_file(p, {".json"}, max_bytes), source=p.name)
        return normalize_bank(raw, default_document=doc_name if isinstance(raw, list) else document, default_subject=subject)
    if suffix == ".csv":
        rows = _csv_records(read_text_file(p, {".csv"}, max_bytes))
        return normalize_bank(rows, default_document=doc_name, default_subject=subject)
    if suffix in (".md", ".markdown", ".txt"):
        raw = parse_text_exam(read_text_file(p, {".md", ".markdown", ".txt"}, max_bytes), doc_name)
        if not raw["questions"]:
            raise InputError(
                f"No numbered questions found in {p.name}. The text parser expects lines like '1. ...' "
                "with optional '[3 marks]'. Ask the agent to produce a structured JSON bank instead."
            )
        return normalize_bank(raw, default_subject=subject, origin="agent_extracted", default_provenance="explicit")
    raise InputError(f"Unsupported source type '{suffix}'. Supported: .json .csv .md .txt (.pdf with optional pypdf)")


def extract_pdf_text(path: str | Path, max_bytes: int = MAX_INPUT_BYTES) -> str:
    """Extract text from a PDF using the optional ``pypdf`` package."""
    p = Path(path)
    if not p.is_file():
        raise InputError(f"Input file not found: {path}")
    if p.stat().st_size > max_bytes:
        raise InputError(f"{p.name} exceeds the {max_bytes}-byte input limit")
    with p.open("rb") as fh:
        if fh.read(5) != b"%PDF-":
            raise InputError(f"{p.name} does not look like a PDF file")
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise InputError(
            "PDF text extraction needs the optional 'pypdf' package (pip install pypdf). "
            "Without it, let the agent read the PDF directly and write a JSON question bank."
        ) from exc
    reader = PdfReader(str(p))
    pages = []
    for i, page in enumerate(reader.pages):
        pages.append(page.extract_text() or "")
        if i >= 500:
            break
    text = "\n".join(pages)
    if not text.strip():
        raise InputError(f"No extractable text in {p.name} (scanned image?). Use the agent's vision to transcribe it.")
    return text
