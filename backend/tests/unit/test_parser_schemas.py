"""Unit tests for parser output schemas (P1 — task 2.1.1).

Run via:
  make test-parser-schemas
"""
from __future__ import annotations

import json
from datetime import date

import pytest

from agent_system.parser.schemas import (
    DocumentFieldsOutput,
    DocumentType,
    IncidentType,
    IntakeOutput,
    SchemaViolationError,
    VisionObservationOutput,
    parse_strict,
)
from agent_system.parser.schemas.vision import DamageSeverity, DamageZone

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _intake(**overrides) -> dict:
    base = {
        "schema_version": "intake@2",
        "intent": "new_claim",
        "incident_type": "collision",
        "incident_date": "2025-03-15",
        "incident_location": "Main St, Springfield",
        "damage_description": "Front bumper cracked.",
        "police_report_filed": True,
        "other_parties_involved": True,
        "injuries_reported": False,
        "intake_complete": True,
        "missing_fields": [],
    }
    base.update(overrides)
    return base


def _document(**overrides) -> dict:
    base = {
        "schema_version": "document_fields@1",
        "document_type": "police_report",
        "incident_date": "2025-03-15",
        "parties_mentioned": ["Alice", "Bob"],
        "damage_items": ["front bumper"],
        "total_amount": 1500.0,
        "narrative_summary": "Vehicle struck at intersection.",
        "flagged_phrases": [],
    }
    base.update(overrides)
    return base


def _vision(**overrides) -> dict:
    base = {
        "schema_version": "vision_observation@1",
        "damage_observed": True,
        "damage_zones": ["front"],
        "severity": "moderate",
        "confidence": 0.87,
        "observation_notes": "Visible crumple zone deformation.",
        "text_regions_detected": False,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# SchemaViolationError structure
# ---------------------------------------------------------------------------


class TestSchemaViolationError:
    def test_is_exception(self):
        e = SchemaViolationError(
            "msg", schema_name="intake@1", field_path="incident_date",
            error_kind="missing", raw_excerpt="{}",
        )
        assert isinstance(e, Exception)

    def test_attributes_preserved(self):
        e = SchemaViolationError(
            "bad", schema_name="intake@1", field_path="foo",
            error_kind="type", raw_excerpt="x" * 300,
        )
        assert e.schema_name == "intake@1"
        assert e.field_path == "foo"
        assert e.error_kind == "type"

    def test_raw_excerpt_truncated_to_200(self):
        e = SchemaViolationError(
            "msg", schema_name="x", field_path=None,
            error_kind="value", raw_excerpt="A" * 500,
        )
        assert len(e.raw_excerpt) == 200

    def test_short_excerpt_not_padded(self):
        e = SchemaViolationError(
            "msg", schema_name="x", field_path=None,
            error_kind="value", raw_excerpt="short",
        )
        assert e.raw_excerpt == "short"

    def test_message_in_str(self):
        e = SchemaViolationError(
            "hash mismatch for agent X", schema_name="x", field_path=None,
            error_kind="value", raw_excerpt="",
        )
        assert "hash mismatch" in str(e)

    def test_field_path_none_allowed(self):
        e = SchemaViolationError(
            "msg", schema_name="x", field_path=None,
            error_kind="invalid_json", raw_excerpt="",
        )
        assert e.field_path is None


# ---------------------------------------------------------------------------
# parse_strict — invalid JSON
# ---------------------------------------------------------------------------


class TestParseStrictInvalidJson:
    def test_not_json_raises(self):
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict("not json", IntakeOutput)
        assert exc_info.value.error_kind == "invalid_json"

    def test_empty_string_raises(self):
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict("", IntakeOutput)
        assert exc_info.value.error_kind == "invalid_json"

    def test_truncated_json_raises(self):
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict('{"schema_version": "intake@1"', IntakeOutput)
        assert exc_info.value.error_kind == "invalid_json"

    def test_error_is_schema_violation_not_json_decode(self):
        with pytest.raises(SchemaViolationError):
            parse_strict("{bad}", IntakeOutput)


# ---------------------------------------------------------------------------
# IntakeOutput — happy path
# ---------------------------------------------------------------------------


class TestIntakeOutputHappyPath:
    def test_valid_round_trip(self):
        obj = parse_strict(json.dumps(_intake()), IntakeOutput)
        assert isinstance(obj, IntakeOutput)

    def test_incident_type_enum(self):
        obj = parse_strict(json.dumps(_intake()), IntakeOutput)
        assert obj.incident_type == IncidentType.collision

    def test_incident_date_parsed(self):
        obj = parse_strict(json.dumps(_intake()), IntakeOutput)
        assert obj.incident_date == date(2025, 3, 15)

    def test_nullable_fields_accept_none(self):
        data = _intake(
            incident_date=None,
            incident_location=None,
            police_report_filed=None,
            other_parties_involved=None,
            injuries_reported=None,
        )
        obj = parse_strict(json.dumps(data), IntakeOutput)
        assert obj.incident_date is None
        assert obj.incident_location is None

    def test_missing_fields_defaults_empty(self):
        data = _intake()
        data.pop("missing_fields")
        obj = parse_strict(json.dumps(data), IntakeOutput)
        assert obj.missing_fields == []

    def test_missing_fields_populated(self):
        data = _intake(missing_fields=["police_report_filed"])
        obj = parse_strict(json.dumps(data), IntakeOutput)
        assert "police_report_filed" in obj.missing_fields

    def test_all_incident_types(self):
        for itype in ("collision", "theft", "vandalism", "weather", "fire", "other"):
            obj = parse_strict(json.dumps(_intake(incident_type=itype)), IntakeOutput)
            assert obj.incident_type.value == itype

    def test_schema_version_literal(self):
        obj = parse_strict(json.dumps(_intake()), IntakeOutput)
        assert obj.schema_version == "intake@2"

    def test_damage_description_max_500(self):
        data = _intake(damage_description="x" * 500)
        obj = parse_strict(json.dumps(data), IntakeOutput)
        assert len(obj.damage_description) == 500


# ---------------------------------------------------------------------------
# IntakeOutput — validation failures
# ---------------------------------------------------------------------------


class TestIntakeOutputFailures:
    def test_missing_required_field_raises(self):
        data = _intake()
        del data["incident_type"]
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(json.dumps(data), IntakeOutput)
        assert exc_info.value.error_kind == "missing"

    def test_extra_field_raises(self):
        data = _intake(injected_field="pwned")
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(json.dumps(data), IntakeOutput)
        assert exc_info.value.error_kind == "extra"

    def test_wrong_incident_type_raises(self):
        data = _intake(incident_type="earthquake")
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(json.dumps(data), IntakeOutput)
        assert exc_info.value.error_kind in ("type", "value")

    def test_wrong_schema_version_raises(self):
        data = _intake(schema_version="intake@9")
        with pytest.raises(SchemaViolationError):
            parse_strict(json.dumps(data), IntakeOutput)

    def test_wrong_type_for_bool_raises(self):
        data = _intake(intake_complete="yes")  # string instead of bool
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(json.dumps(data), IntakeOutput)
        assert exc_info.value.error_kind == "type"

    def test_damage_description_too_long_raises(self):
        data = _intake(damage_description="x" * 501)
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(json.dumps(data), IntakeOutput)
        assert exc_info.value.error_kind == "value"

    def test_field_path_in_error(self):
        data = _intake()
        del data["incident_type"]
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(json.dumps(data), IntakeOutput)
        assert exc_info.value.field_path is not None


# ---------------------------------------------------------------------------
# DocumentFieldsOutput — happy path
# ---------------------------------------------------------------------------


class TestDocumentFieldsOutputHappyPath:
    def test_valid_round_trip(self):
        obj = parse_strict(json.dumps(_document()), DocumentFieldsOutput)
        assert isinstance(obj, DocumentFieldsOutput)

    def test_document_type_enum(self):
        obj = parse_strict(json.dumps(_document()), DocumentFieldsOutput)
        assert obj.document_type == DocumentType.police_report

    def test_parties_mentioned_list(self):
        obj = parse_strict(json.dumps(_document()), DocumentFieldsOutput)
        assert obj.parties_mentioned == ["Alice", "Bob"]

    def test_nullable_fields(self):
        data = _document(incident_date=None, total_amount=None)
        obj = parse_strict(json.dumps(data), DocumentFieldsOutput)
        assert obj.incident_date is None
        assert obj.total_amount is None

    def test_default_list_fields(self):
        data = _document()
        data.pop("parties_mentioned")
        data.pop("damage_items")
        data.pop("flagged_phrases")
        obj = parse_strict(json.dumps(data), DocumentFieldsOutput)
        assert obj.parties_mentioned == []
        assert obj.damage_items == []
        assert obj.flagged_phrases == []

    def test_all_document_types(self):
        for dtype in ("police_report", "repair_estimate", "medical_report", "other"):
            obj = parse_strict(json.dumps(_document(document_type=dtype)), DocumentFieldsOutput)
            assert obj.document_type.value == dtype

    def test_narrative_summary_max_1000(self):
        data = _document(narrative_summary="n" * 1000)
        obj = parse_strict(json.dumps(data), DocumentFieldsOutput)
        assert len(obj.narrative_summary) == 1000


# ---------------------------------------------------------------------------
# DocumentFieldsOutput — validation failures
# ---------------------------------------------------------------------------


class TestDocumentFieldsOutputFailures:
    def test_missing_document_type_raises(self):
        data = _document()
        del data["document_type"]
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(json.dumps(data), DocumentFieldsOutput)
        assert exc_info.value.error_kind == "missing"

    def test_extra_field_raises(self):
        data = _document(llm_note="hallucinated")
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(json.dumps(data), DocumentFieldsOutput)
        assert exc_info.value.error_kind == "extra"

    def test_narrative_too_long_raises(self):
        data = _document(narrative_summary="x" * 1001)
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(json.dumps(data), DocumentFieldsOutput)
        assert exc_info.value.error_kind == "value"

    def test_wrong_document_type_raises(self):
        data = _document(document_type="selfie")
        with pytest.raises(SchemaViolationError):
            parse_strict(json.dumps(data), DocumentFieldsOutput)


# ---------------------------------------------------------------------------
# VisionObservationOutput — happy path
# ---------------------------------------------------------------------------


class TestVisionObservationOutputHappyPath:
    def test_valid_round_trip(self):
        obj = parse_strict(json.dumps(_vision()), VisionObservationOutput)
        assert isinstance(obj, VisionObservationOutput)

    def test_damage_zones_enum(self):
        data = _vision(damage_zones=["front", "rear"])
        obj = parse_strict(json.dumps(data), VisionObservationOutput)
        assert DamageZone.front in obj.damage_zones
        assert DamageZone.rear in obj.damage_zones

    def test_severity_enum(self):
        obj = parse_strict(json.dumps(_vision(severity="total_loss")), VisionObservationOutput)
        assert obj.severity == DamageSeverity.total_loss

    def test_severity_none(self):
        data = _vision(severity=None)
        obj = parse_strict(json.dumps(data), VisionObservationOutput)
        assert obj.severity is None

    def test_confidence_bounds(self):
        for val in (0.0, 0.5, 1.0):
            obj = parse_strict(json.dumps(_vision(confidence=val)), VisionObservationOutput)
            assert obj.confidence == val

    def test_empty_damage_zones_default(self):
        data = _vision()
        data.pop("damage_zones")
        obj = parse_strict(json.dumps(data), VisionObservationOutput)
        assert obj.damage_zones == []

    def test_all_damage_zones(self):
        zones = ["front", "rear", "driver_side", "passenger_side", "roof", "interior", "underbody", "multiple"]
        obj = parse_strict(json.dumps(_vision(damage_zones=zones)), VisionObservationOutput)
        assert len(obj.damage_zones) == len(zones)

    def test_all_severities(self):
        for sev in ("minor", "moderate", "severe", "total_loss"):
            obj = parse_strict(json.dumps(_vision(severity=sev)), VisionObservationOutput)
            assert obj.severity.value == sev

    def test_observation_notes_max_500(self):
        data = _vision(observation_notes="o" * 500)
        obj = parse_strict(json.dumps(data), VisionObservationOutput)
        assert len(obj.observation_notes) == 500


# ---------------------------------------------------------------------------
# VisionObservationOutput — validation failures
# ---------------------------------------------------------------------------


class TestVisionObservationOutputFailures:
    def test_extra_field_raises(self):
        data = _vision(llm_comment="looks fine")
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(json.dumps(data), VisionObservationOutput)
        assert exc_info.value.error_kind == "extra"

    def test_confidence_below_zero_raises(self):
        data = _vision(confidence=-0.01)
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(json.dumps(data), VisionObservationOutput)
        assert exc_info.value.error_kind == "value"

    def test_confidence_above_one_raises(self):
        data = _vision(confidence=1.01)
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(json.dumps(data), VisionObservationOutput)
        assert exc_info.value.error_kind == "value"

    def test_confidence_wrong_type_raises(self):
        data = _vision(confidence="high")
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(json.dumps(data), VisionObservationOutput)
        # float field with a non-numeric string gives "type" or "value" depending on Pydantic internals
        assert exc_info.value.error_kind in ("type", "value")

    def test_invalid_damage_zone_raises(self):
        data = _vision(damage_zones=["front", "bumper"])
        with pytest.raises(SchemaViolationError):
            parse_strict(json.dumps(data), VisionObservationOutput)

    def test_observation_notes_too_long_raises(self):
        data = _vision(observation_notes="x" * 501)
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(json.dumps(data), VisionObservationOutput)
        assert exc_info.value.error_kind == "value"

    def test_missing_damage_observed_raises(self):
        data = _vision()
        del data["damage_observed"]
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(json.dumps(data), VisionObservationOutput)
        assert exc_info.value.error_kind == "missing"


# ---------------------------------------------------------------------------
# parse_strict — schema_name surfaces correctly
# ---------------------------------------------------------------------------


class TestParseStrictSchemaName:
    def test_schema_name_in_error_for_intake(self):
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict("{}", IntakeOutput)
        assert "intake" in exc_info.value.schema_name.lower() or \
               exc_info.value.schema_name == "IntakeOutput"

    def test_schema_name_in_error_for_document(self):
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict("{}", DocumentFieldsOutput)
        assert exc_info.value.schema_name  # non-empty

    def test_raw_excerpt_captured_on_failure(self):
        raw = json.dumps(_intake(incident_type="earthquake"))
        with pytest.raises(SchemaViolationError) as exc_info:
            parse_strict(raw, IntakeOutput)
        assert len(exc_info.value.raw_excerpt) > 0

    def test_pydantic_validation_error_does_not_leak(self):
        from pydantic import ValidationError
        data = _intake()
        del data["incident_type"]
        with pytest.raises(SchemaViolationError):
            parse_strict(json.dumps(data), IntakeOutput)
        # Confirm ValidationError doesn't propagate (would be caught above)

    def test_json_decode_error_does_not_leak(self):
        import json as _json
        with pytest.raises(SchemaViolationError):
            parse_strict("bad json", IntakeOutput)
        # Confirm raw JSONDecodeError doesn't propagate


# ---------------------------------------------------------------------------
# Frozen model / immutability
# ---------------------------------------------------------------------------


class TestImmutability:
    def test_intake_output_is_frozen(self):
        from pydantic import ValidationError as PydanticValidationError
        obj = parse_strict(json.dumps(_intake()), IntakeOutput)
        with pytest.raises((TypeError, AttributeError, ValueError, PydanticValidationError)):
            obj.incident_type = "theft"  # type: ignore[misc]

    def test_document_output_is_frozen(self):
        from pydantic import ValidationError as PydanticValidationError
        obj = parse_strict(json.dumps(_document()), DocumentFieldsOutput)
        with pytest.raises((TypeError, AttributeError, ValueError, PydanticValidationError)):
            obj.document_type = "other"  # type: ignore[misc]

    def test_vision_output_is_frozen(self):
        from pydantic import ValidationError as PydanticValidationError
        obj = parse_strict(json.dumps(_vision()), VisionObservationOutput)
        with pytest.raises((TypeError, AttributeError, ValueError, PydanticValidationError)):
            obj.confidence = 0.5  # type: ignore[misc]
