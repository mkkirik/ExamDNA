"""A small, dependency-free JSON Schema validator.

Supports the subset of JSON Schema (draft-07 style) used by ExamDNA schemas:
``type`` (string or list), ``properties``, ``required``,
``additionalProperties`` (bool or schema), ``items``, ``enum``, ``const``,
``minimum``, ``maximum``, ``minLength``, ``maxLength``, ``pattern``,
``minItems``, ``maxItems``, ``uniqueItems``, ``anyOf`` and local ``$ref``
(``#/definitions/...``). Unknown keywords are ignored, as in JSON Schema.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"
SCHEMA_NAMES = [
    "question",
    "question_bank",
    "genome",
    "mutation_spec",
    "mutation_plan",
    "candidate",
    "compile_config",
    "exam_dna",
]
MAX_ERRORS = 50


class SchemaError(ValueError):
    def __init__(self, errors: List[str]):
        self.errors = errors
        preview = "; ".join(errors[:5])
        more = f" (+{len(errors) - 5} more)" if len(errors) > 5 else ""
        super().__init__(f"Schema validation failed: {preview}{more}")


@lru_cache(maxsize=None)
def load_schema(name: str) -> Dict[str, Any]:
    if name not in SCHEMA_NAMES:
        raise KeyError(f"Unknown schema '{name}'. Known: {', '.join(SCHEMA_NAMES)}")
    path = SCHEMA_DIR / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def _resolve(ref: str, root: Dict[str, Any]) -> Dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"Only local $ref is supported, got {ref}")
    node: Any = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _validate(value: Any, schema: Dict[str, Any], root: Dict[str, Any], path: str, errors: List[str]) -> None:
    if len(errors) >= MAX_ERRORS:
        return
    if "$ref" in schema:
        schema = _resolve(schema["$ref"], root)

    if "anyOf" in schema:
        for option in schema["anyOf"]:
            trial: List[str] = []
            _validate(value, option, root, path, trial)
            if not trial:
                break
        else:
            errors.append(f"{path}: does not match any allowed form")
            return

    expected = schema.get("type")
    if expected is not None:
        types = expected if isinstance(expected, list) else [expected]
        if not any(_TYPE_CHECKS[t](value) for t in types):
            errors.append(f"{path}: expected {' or '.join(types)}, got {type(value).__name__}")
            return

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not one of {schema['enum']}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']} characters")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']} characters")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: {value[:40]!r} does not match pattern {schema['pattern']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} is below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} is above maximum {schema['maximum']}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: needs at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: has more than {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            seen = [json.dumps(v, sort_keys=True) for v in value]
            if len(seen) != len(set(seen)):
                errors.append(f"{path}: items must be unique")
        if "items" in schema:
            for i, item in enumerate(value):
                _validate(item, schema["items"], root, f"{path}[{i}]", errors)

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required field '{key}'")
        props = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in props:
                _validate(item, props[key], root, f"{path}.{key}", errors)
            elif additional is False:
                errors.append(f"{path}: unexpected field '{key}'")
            elif isinstance(additional, dict):
                _validate(item, additional, root, f"{path}.{key}", errors)


def validate(value: Any, schema_name_or_schema: Any) -> List[str]:
    """Return a list of human-readable errors (empty when valid)."""
    schema = load_schema(schema_name_or_schema) if isinstance(schema_name_or_schema, str) else schema_name_or_schema
    errors: List[str] = []
    _validate(value, schema, schema, "$", errors)
    return errors


def validate_or_raise(value: Any, schema_name: str) -> None:
    errors = validate(value, schema_name)
    if errors:
        raise SchemaError(errors)
