"""Normalization of raw question records into the canonical question schema.

Rules
-----
* Missing information stays missing: unknown marks are ``None`` and the field
  is listed in ``missing_fields``. Nothing is invented.
* Every populated semantic field carries a provenance label:
  ``explicit`` (stated in a source), ``inferred`` (judged by the agent),
  ``calculated`` (derived by this software) or ``unverified``.
* Text is scanned for instruction-like content; matches are recorded in
  ``security_flags`` and never acted upon.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Optional, Tuple

from .. import SCHEMA_VERSION
from ..models.constants import (
    COGNITIVE_LEVELS,
    PROVENANCE_KINDS,
    QUESTION_TYPE_ALIASES,
    QUESTION_TYPES,
)
from ..models.schema import validate
from ..utilities.ids import is_valid_id, slugify, stable_id
from ..utilities.io import InputError
from ..utilities.textsafety import scan_for_injection

FIELD_ALIASES = {
    "question": "text",
    "prompt": "text",
    "stem": "text",
    "body": "text",
    "type": "question_type",
    "qtype": "question_type",
    "mark": "marks",
    "points": "marks",
    "score": "marks",
    "max_marks": "marks",
    "objectives": "learning_objectives",
    "learning_objective": "learning_objectives",
    "lo": "learning_objectives",
    "cognitive": "cognitive_level",
    "paper": "document",
    "source_document": "document",
}

SEMANTIC_FIELDS = [
    "subject",
    "topic",
    "subtopic",
    "question_type",
    "marks",
    "section",
    "learning_objectives",
    "cognitive_level",
    "given",
    "required_output",
    "constraints",
    "marking",
]

MAX_QUESTIONS = 5000
_MARKS_RE = re.compile(r"^\s*\[?\(?\s*(\d{1,3})\s*(marks?|pts?|points?)?\s*\)?\]?\s*$", re.IGNORECASE)


def _parse_marks(value: Any) -> Tuple[Optional[int], Optional[str]]:
    if value is None or value == "":
        return None, None
    if isinstance(value, bool):
        return None, "marks must be a number"
    if isinstance(value, int):
        return (value, None) if 0 <= value <= 500 else (None, f"marks value {value} out of range")
    if isinstance(value, float):
        if value.is_integer() and 0 <= value <= 500:
            return int(value), None
        return None, f"non-integer marks value {value}"
    if isinstance(value, str):
        m = _MARKS_RE.match(value)
        if m:
            return int(m.group(1)), None
    return None, f"could not parse marks from {value!r}"


def _as_list(value: Any) -> List[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [v.strip() for v in re.split(r"[;|\n]", value) if v.strip()]
    return [value]


def _normalize_type(value: Any) -> Tuple[Optional[str], Optional[str]]:
    if value is None or value == "":
        return None, None
    key = str(value).strip().lower().replace(" ", "_")
    if key in QUESTION_TYPES:
        return key, None
    alias = QUESTION_TYPE_ALIASES.get(key) or QUESTION_TYPE_ALIASES.get(key.replace("_", "-"))
    if alias:
        return alias, None
    return None, f"unknown question type {value!r}"


def _normalize_cognitive(value: Any) -> Tuple[Optional[str], Optional[str]]:
    if value is None or value == "":
        return None, None
    key = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    if key in COGNITIVE_LEVELS:
        return key, None
    return None, f"unknown cognitive level {value!r}"


def _normalize_given(items: Any, issues: List[str]) -> List[Dict[str, Any]]:
    result = []
    for item in _as_list(items):
        if not isinstance(item, dict) or "symbol" not in item:
            issues.append(f"ignored malformed 'given' entry: {str(item)[:60]}")
            continue
        entry = {
            "symbol": str(item["symbol"]),
            "description": item.get("description"),
            "value": item.get("value"),
            "unit": item.get("unit"),
        }
        if "role" in item:
            entry["role"] = item["role"]
        if isinstance(entry["value"], bool) or (entry["value"] is not None and not isinstance(entry["value"], (int, float))):
            issues.append(f"given '{entry['symbol']}' has non-numeric value; set to null")
            entry["value"] = None
        result.append(entry)
    return result


def _normalize_constraints(items: Any) -> List[Dict[str, Any]]:
    result = []
    for item in _as_list(items):
        if isinstance(item, str):
            result.append({"text": item})
        elif isinstance(item, dict) and item.get("text"):
            entry = {"text": str(item["text"])}
            for key in ("var", "op", "value", "kind"):
                if key in item:
                    entry[key] = item[key]
            result.append(entry)
    return result


def normalize_question(
    raw: Dict[str, Any],
    *,
    default_document: Optional[str] = None,
    default_subject: Optional[str] = None,
    position: int = 0,
    origin: str = "source",
    default_provenance: str = "explicit",
) -> Tuple[Dict[str, Any], List[str]]:
    """Normalize one raw record. Returns ``(question, issues)``.

    ``default_provenance`` applies to fields that are present but carry no
    provenance label: ``explicit`` for structured banks typed from a source,
    ``unverified`` for anything of unknown origin.
    """
    if not isinstance(raw, dict):
        raise InputError(f"question #{position} is not an object")
    if default_provenance not in PROVENANCE_KINDS:
        raise ValueError(f"invalid default provenance {default_provenance}")

    data: Dict[str, Any] = {}
    for key, value in raw.items():
        data[FIELD_ALIASES.get(key, key)] = value

    issues: List[str] = []
    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        raise InputError(f"question #{position} has no question text")
    text = text.strip()

    source_in = data.get("source") if isinstance(data.get("source"), dict) else {}
    document = source_in.get("document") or data.get("document") or default_document
    raw_id = data.get("id")
    if raw_id is not None and not is_valid_id(str(raw_id)):
        issues.append(f"invalid id {str(raw_id)[:40]!r} replaced with a generated id")
        raw_id = None
    qid = str(raw_id) if raw_id is not None else stable_id(f"q-{slugify(document or 'doc', 16)}", document, position, text)

    marks, err = _parse_marks(data.get("marks"))
    if err:
        issues.append(f"{qid}: {err}")
    qtype, err = _normalize_type(data.get("question_type"))
    if err:
        issues.append(f"{qid}: {err}")
    cognitive, err = _normalize_cognitive(data.get("cognitive_level"))
    if err:
        issues.append(f"{qid}: {err}")

    parts = []
    for i, part in enumerate(_as_list(data.get("parts"))):
        if not isinstance(part, dict) or not part.get("text"):
            issues.append(f"{qid}: ignored malformed part #{i}")
            continue
        p_marks, p_err = _parse_marks(part.get("marks"))
        if p_err:
            issues.append(f"{qid} part {part.get('label', i)}: {p_err}")
        entry = {"label": str(part.get("label") or chr(ord("a") + i)), "text": str(part["text"]).strip(), "marks": p_marks}
        if "answer_space_lines" in part:
            entry["answer_space_lines"] = part["answer_space_lines"]
        parts.append(entry)

    in_prov = data.get("provenance") if isinstance(data.get("provenance"), dict) else {}
    provenance: Dict[str, str] = {"text": in_prov.get("text", default_provenance) if in_prov.get("text") in PROVENANCE_KINDS else default_provenance}

    if marks is None and parts and all(p["marks"] is not None for p in parts):
        marks = sum(p["marks"] for p in parts)
        provenance["marks"] = "calculated"
        issues.append(f"{qid}: total marks calculated from part marks ({marks})")

    marking_in = data.get("marking") if isinstance(data.get("marking"), dict) else None
    marking = None
    if marking_in is not None:
        points = []
        for pt in _as_list(marking_in.get("points")):
            if isinstance(pt, dict) and pt.get("description"):
                pm, perr = _parse_marks(pt.get("marks", 1))
                if perr or pm is None:
                    issues.append(f"{qid}: marking point has invalid marks")
                    continue
                entry = {"description": str(pt["description"]), "marks": pm}
                if pt.get("part") is not None:
                    entry["part"] = str(pt["part"])
                points.append(entry)
        marking = {
            "scheme_available": bool(marking_in.get("scheme_available", bool(points or marking_in.get("final_answer")))),
            "final_answer": marking_in.get("final_answer"),
            "answer_key": marking_in.get("answer_key"),
            "worked_solution": marking_in.get("worked_solution"),
            "points": points,
            "accept_rule": marking_in.get("accept_rule"),
        }

    question: Dict[str, Any] = {
        "id": qid,
        "schema_version": SCHEMA_VERSION,
        "language": data.get("language"),
        "source": {
            "document": document,
            "page": source_in.get("page", data.get("page")),
            "section": source_in.get("section", data.get("section")),
            "position": position,
            "origin": source_in.get("origin", origin) if source_in.get("origin") in ("source", "agent_extracted", "generated") else origin,
        },
        "subject": data.get("subject") or default_subject,
        "topic": data.get("topic"),
        "subtopic": data.get("subtopic"),
        "text": text,
        "question_type": qtype,
        "marks": marks,
        "section": data.get("section"),
        "learning_objectives": [str(x) for x in _as_list(data.get("learning_objectives"))],
        "cognitive_level": cognitive,
        "given": _normalize_given(data.get("given"), issues),
        "required_output": data.get("required_output"),
        "constraints": _normalize_constraints(data.get("constraints")),
        "options": [o for o in _as_list(data.get("options")) if isinstance(o, dict)],
        "parts": parts,
        "table": data.get("table"),
        "diagram_description": data.get("diagram_description"),
        "marking": marking,
        "difficulty_features": data.get("difficulty_features"),
        "extraction_confidence": data.get("extraction_confidence") or ("high" if origin == "source" else "medium"),
        "evidence": [e for e in _as_list(data.get("evidence")) if isinstance(e, dict)],
        "review_status": data.get("review_status") or "unreviewed",
        "provenance": provenance,
        "missing_fields": [],
        "security_flags": [],
        "lineage": data.get("lineage"),
        "validation": data.get("validation"),
    }
    if isinstance(data.get("extensions"), dict):
        question["extensions"] = data["extensions"]

    for fld in SEMANTIC_FIELDS:
        value = question.get(fld)
        empty = value is None or value == [] or value == ""
        if empty:
            question["missing_fields"].append(fld)
        elif fld not in provenance:
            label = in_prov.get(fld)
            provenance[fld] = label if label in PROVENANCE_KINDS else default_provenance
    if question["subject"] and not data.get("subject") and default_subject:
        provenance["subject"] = "inferred"

    flags = set(scan_for_injection(text))
    for part in parts:
        flags.update(scan_for_injection(part["text"]))
    question["security_flags"] = sorted(flags)
    if flags:
        question["review_status"] = "needs_review"
        issues.append(f"{qid}: instruction-like text detected ({', '.join(sorted(flags))}); treated as data only")

    if marks is not None and parts and all(p["marks"] is not None for p in parts):
        if sum(p["marks"] for p in parts) != marks:
            issues.append(f"{qid}: part marks sum to {sum(p['marks'] for p in parts)} but question marks are {marks}")

    errors = validate(question, "question")
    if errors:
        raise InputError(f"question {qid} failed schema validation: {'; '.join(errors[:5])}")
    return question, issues


def normalize_bank(
    raw: Any,
    *,
    default_document: Optional[str] = None,
    default_subject: Optional[str] = None,
    origin: str = "source",
    default_provenance: str = "explicit",
    bank_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Normalize a raw bank (a list of records or ``{"questions": [...]}``)."""
    if isinstance(raw, list):
        records, meta = raw, {}
    elif isinstance(raw, dict) and isinstance(raw.get("questions"), list):
        records, meta = raw["questions"], raw
    else:
        raise InputError("question bank must be a list or an object with a 'questions' list")
    if len(records) > MAX_QUESTIONS:
        raise InputError(f"question bank has {len(records)} questions; limit is {MAX_QUESTIONS}")

    questions: List[Dict[str, Any]] = []
    issues: List[str] = []
    seen: Dict[str, int] = {}
    conflicts: List[str] = []
    for i, record in enumerate(records):
        q, q_issues = normalize_question(
            copy.deepcopy(record),
            default_document=default_document or meta.get("default_document"),
            default_subject=default_subject or meta.get("subject"),
            position=i,
            origin=origin,
            default_provenance=default_provenance,
        )
        if q["id"] in seen:
            conflicts.append(q["id"])
        seen[q["id"]] = i
        questions.append(q)
        issues.extend(q_issues)
    if conflicts:
        raise InputError(f"conflicting question identifiers: {', '.join(sorted(set(conflicts)))}")

    documents = []
    known = {d.get("name") for d in meta.get("source_documents", []) if isinstance(d, dict)}
    for d in meta.get("source_documents", []):
        if isinstance(d, dict) and d.get("name"):
            documents.append({k: d[k] for k in ("name", "kind", "paper_id", "notes") if k in d})
    for q in questions:
        name = q["source"]["document"]
        if name and name not in known:
            documents.append({"name": name, "kind": "exam"})
            known.add(name)

    bank = {
        "schema_version": SCHEMA_VERSION,
        "bank_id": bank_id or meta.get("bank_id") or stable_id("bank", [q["id"] for q in questions]),
        "title": meta.get("title"),
        "source_documents": documents,
        "questions": questions,
        "normalization_report": {
            "question_count": len(questions),
            "issues": issues,
            "missing_marks": [q["id"] for q in questions if q["marks"] is None],
            "security_flagged": [q["id"] for q in questions if q["security_flags"]],
        },
    }
    errors = validate(bank, "question_bank")
    if errors:
        raise InputError(f"bank failed schema validation: {'; '.join(errors[:5])}")
    return bank


def merge_banks(banks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge already-normalized banks, rejecting conflicting IDs."""
    questions: List[Dict[str, Any]] = []
    documents: List[Dict[str, Any]] = []
    issues: List[str] = []
    seen = set()
    names = set()
    for bank in banks:
        for q in bank["questions"]:
            if q["id"] in seen:
                raise InputError(f"conflicting question identifier across inputs: {q['id']}")
            seen.add(q["id"])
            questions.append(q)
        for d in bank.get("source_documents", []):
            if d["name"] not in names:
                names.add(d["name"])
                documents.append(d)
        issues.extend(bank.get("normalization_report", {}).get("issues", []))
    return {
        "schema_version": SCHEMA_VERSION,
        "bank_id": stable_id("bank", sorted(seen)),
        "title": None,
        "source_documents": documents,
        "questions": questions,
        "normalization_report": {
            "question_count": len(questions),
            "issues": issues,
            "missing_marks": [q["id"] for q in questions if q["marks"] is None],
            "security_flagged": [q["id"] for q in questions if q.get("security_flags")],
        },
    }
