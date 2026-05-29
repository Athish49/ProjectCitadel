"""Parser output schemas (P1 — task 2.1.1)."""
from agent_system.parser.schemas.document import DocumentFieldsOutput, DocumentType
from agent_system.parser.schemas.intake import IncidentType, IntakeOutput
from agent_system.parser.schemas.violations import SchemaViolationError, parse_strict
from agent_system.parser.schemas.vision import (
    DamageSeverity,
    DamageZone,
    VisionObservationOutput,
)

__all__ = [
    "DocumentFieldsOutput",
    "DocumentType",
    "IncidentType",
    "IntakeOutput",
    "SchemaViolationError",
    "parse_strict",
    "DamageSeverity",
    "DamageZone",
    "VisionObservationOutput",
]
