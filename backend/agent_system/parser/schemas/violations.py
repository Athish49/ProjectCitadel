"""Schema violation handling for parser outputs (P1 — task 2.1.1).

SchemaViolationError is the single error type callers catch.  It carries
structured fields for audit logging.  Pydantic internals never escape this
module — callers only see SchemaViolationError.
"""
from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

_RAW_EXCERPT_MAX = 200


class SchemaViolationError(Exception):
    """Raised when parser output fails schema validation.

    Fields are structured for audit logging — never pass raw_excerpt to an LLM.
    """

    def __init__(
        self,
        message: str,
        *,
        schema_name: str,
        field_path: str | None,
        error_kind: str,
        raw_excerpt: str,
    ) -> None:
        super().__init__(message)
        self.schema_name = schema_name
        self.field_path = field_path
        # "missing" | "extra" | "type" | "value" | "invalid_json"
        self.error_kind = error_kind
        # Truncated to _RAW_EXCERPT_MAX chars — still untrusted; log only, never pass forward
        self.raw_excerpt = raw_excerpt[:_RAW_EXCERPT_MAX]


def _map_pydantic_error_kind(pydantic_type: str) -> str:
    if pydantic_type == "missing":
        return "missing"
    if pydantic_type == "extra_forbidden":
        return "extra"
    # Strict() annotation (StrictBool etc.) emits is_instance_of
    if pydantic_type in ("is_instance_of", "is_subclass_of"):
        return "type"
    if pydantic_type.endswith("_type"):
        return "type"
    # "value_error", "literal_error", "enum", "float_parsing", etc.
    return "value"


def parse_strict(raw_json: str, schema_class: type[T]) -> T:
    """Parse *raw_json* into *schema_class* with Pydantic lax validation.

    Raises SchemaViolationError on any failure — callers never see
    json.JSONDecodeError or pydantic.ValidationError.

    Uses lax (non-strict) mode so string→enum and string→date coercions
    work for LLM JSON output.  Individual bool fields use StrictBool to
    prevent "yes"/"no" string coercion at the field level.
    """
    schema_name: str = getattr(schema_class, "_schema_name", None) or schema_class.__name__
    excerpt = raw_json[:_RAW_EXCERPT_MAX]

    try:
        data: Any = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise SchemaViolationError(
            f"Invalid JSON for schema {schema_name!r}: {exc}",
            schema_name=schema_name,
            field_path=None,
            error_kind="invalid_json",
            raw_excerpt=excerpt,
        ) from exc

    try:
        return schema_class.model_validate(data)
    except ValidationError as exc:
        first = exc.errors(include_url=False)[0]
        loc = first.get("loc", ())
        field_path = ".".join(str(p) for p in loc) if loc else None
        error_kind = _map_pydantic_error_kind(first.get("type", ""))
        raise SchemaViolationError(
            f"Schema violation in {schema_name!r}"
            + (f" at {field_path!r}" if field_path else "")
            + f": {first.get('msg', '')}",
            schema_name=schema_name,
            field_path=field_path,
            error_kind=error_kind,
            raw_excerpt=excerpt,
        ) from exc
