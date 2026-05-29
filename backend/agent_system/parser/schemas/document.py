"""Document-fields parser output schema (P1 — task 2.1.1).

The quarantined parser LLM produces JSON conforming to DocumentFieldsOutput
after extracting structured fields from a supporting document (police report,
repair estimate, medical report, etc.).
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(str, Enum):
    police_report = "police_report"
    repair_estimate = "repair_estimate"
    medical_report = "medical_report"
    other = "other"


class DocumentFieldsOutput(BaseModel):
    """Structured fields extracted from a supporting claim document."""

    _schema_name: ClassVar[str] = "document_fields@1"

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["document_fields@1"]
    document_type: DocumentType
    incident_date: date | None
    parties_mentioned: list[str] = Field(default_factory=list)
    damage_items: list[str] = Field(default_factory=list)
    total_amount: float | None
    narrative_summary: Annotated[str, Field(max_length=1000)]
    flagged_phrases: list[str] = Field(default_factory=list)
