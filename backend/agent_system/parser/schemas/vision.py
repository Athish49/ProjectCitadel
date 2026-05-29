"""Vision-observation parser output schema (P1 — task 2.1.1).

The quarantined vision LLM produces JSON conforming to VisionObservationOutput
after analysing a damage photograph.
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool


class DamageZone(str, Enum):
    front = "front"
    rear = "rear"
    driver_side = "driver_side"
    passenger_side = "passenger_side"
    roof = "roof"
    interior = "interior"
    underbody = "underbody"
    multiple = "multiple"


class DamageSeverity(str, Enum):
    minor = "minor"
    moderate = "moderate"
    severe = "severe"
    total_loss = "total_loss"


class VisionObservationOutput(BaseModel):
    """Structured damage observations from a vehicle photo analysis."""

    _schema_name: ClassVar[str] = "vision_observation@1"

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["vision_observation@1"]
    damage_observed: StrictBool
    damage_zones: list[DamageZone] = Field(default_factory=list)
    severity: DamageSeverity | None
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    observation_notes: Annotated[str, Field(max_length=500)]
    text_regions_detected: StrictBool
