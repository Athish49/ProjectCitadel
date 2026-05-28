"""Unit tests for audit.chain — no database required."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

import hashlib
import json
import uuid
from datetime import datetime, timezone

import pytest

from audit.chain import (
    GENESIS_HASH,
    _serialize,
    canonical_fields,
    compute_row_hash,
)


class TestSerialize:
    def test_datetime_converted_to_utc_iso(self):
        from datetime import timedelta
        eastern = timezone(timedelta(hours=-5))
        dt = datetime(2025, 6, 1, 12, 0, 0, tzinfo=eastern)
        result = _serialize(dt)
        assert result == "2025-06-01T17:00:00+00:00"

    def test_datetime_already_utc(self):
        dt = datetime(2025, 6, 1, 17, 0, 0, tzinfo=timezone.utc)
        result = _serialize(dt)
        assert result == "2025-06-01T17:00:00+00:00"

    def test_uuid_becomes_str(self):
        u = uuid.UUID("12345678-1234-5678-1234-567812345678")
        assert _serialize(u) == "12345678-1234-5678-1234-567812345678"

    def test_str_passthrough(self):
        assert _serialize("hello") == "hello"

    def test_int_passthrough(self):
        assert _serialize(42) == 42

    def test_none_passthrough(self):
        assert _serialize(None) is None

    def test_bool_passthrough(self):
        assert _serialize(True) is True


class TestCanonicalFields:
    def _base_row(self) -> dict:
        return {
            "log_id": 1,
            "trace_id": None,
            "prev_hash": GENESIS_HASH,
            "agent_id": "orchestrator",
            "action": "claim_stage_updated",
            "target": "claims/abc",
            "details": {"old": "INTAKE", "new": "PROCESSING"},
            "data_label": "CONFIDENTIAL",
            "security_event": False,
        }

    def test_deterministic(self):
        row = self._base_row()
        assert canonical_fields(row) == canonical_fields(row)

    def test_row_hash_excluded(self):
        row = self._base_row()
        row["row_hash"] = "deadbeef" * 8
        result = canonical_fields(row)
        assert "row_hash" not in json.loads(result)

    def test_key_order_independent(self):
        row1 = self._base_row()
        row2 = {k: row1[k] for k in reversed(list(row1.keys()))}
        assert canonical_fields(row1) == canonical_fields(row2)

    def test_value_change_changes_output(self):
        row = self._base_row()
        original = canonical_fields(row)
        row["action"] = "DIFFERENT"
        assert canonical_fields(row) != original

    def test_none_detail_serializes_as_null(self):
        row = self._base_row()
        row["details"] = None
        parsed = json.loads(canonical_fields(row))
        assert parsed["details"] is None


class TestComputeRowHash:
    def _row(self) -> dict:
        return {
            "log_id": 1,
            "trace_id": None,
            "prev_hash": GENESIS_HASH,
            "agent_id": "intake_actor",
            "action": "claim_created",
            "target": "claims/xyz",
            "details": None,
            "data_label": "CONFIDENTIAL",
            "security_event": False,
        }

    def test_returns_64_char_hex(self):
        h = compute_row_hash(GENESIS_HASH, self._row())
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self):
        row = self._row()
        assert compute_row_hash(GENESIS_HASH, row) == compute_row_hash(GENESIS_HASH, row)

    def test_different_prev_hash_different_result(self):
        row = self._row()
        h1 = compute_row_hash(GENESIS_HASH, row)
        h2 = compute_row_hash("a" * 64, row)
        assert h1 != h2

    def test_field_change_changes_hash(self):
        row = self._row()
        h1 = compute_row_hash(GENESIS_HASH, row)
        row["action"] = "tampered"
        h2 = compute_row_hash(GENESIS_HASH, row)
        assert h1 != h2

    def test_matches_manual_sha256(self):
        row = self._row()
        payload = (GENESIS_HASH + canonical_fields(row)).encode("utf-8")
        expected = hashlib.sha256(payload).hexdigest()
        assert compute_row_hash(GENESIS_HASH, row) == expected

    def test_genesis_hash_is_64_zeros(self):
        assert GENESIS_HASH == "0" * 64
