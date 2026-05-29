"""Intake parser output schema (P1 — task 2.1.1).

The quarantined parser LLM produces JSON conforming to IntakeOutput.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool


class IncidentType(str, Enum):
    collision = "collision"
    theft = "theft"
    vandalism = "vandalism"
    weather = "weather"
    fire = "fire"
    other = "other"


class IntakeOutput(BaseModel):
    """Structured claim intake extracted from claimant's free-form submission."""

    _schema_name: ClassVar[str] = "intake@1"

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["intake@1"]
    incident_type: IncidentType
    incident_date: date | None
    incident_location: str | None
    damage_description: Annotated[str, Field(max_length=500)]
    police_report_filed: StrictBool | None
    other_parties_involved: StrictBool | None
    injuries_reported: StrictBool | None
    intake_complete: StrictBool
    missing_fields: list[str] = Field(default_factory=list)
