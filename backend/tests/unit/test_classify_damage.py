"""Unit tests for classify_damage tool (Sprint 4.1.1).

Tests cover:
  - Pure function: determinism, full label coverage, confidence range, IFC output shape
  - ToolRegistry integration: token gate passes, audit row written, Labeled value propagated
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from agent_system.identity.keys import KeypairManager
from agent_system.ifc.labels import DataLabel, Labeled
from agent_system.tools.capability_tokens import issue_token
from agent_system.tools.implementations.claims_tools import (
    _DAMAGE_LABELS,
    classify_damage,
)
from agent_system.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conn(used_at=None, row_exists=True):
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchone.return_value = (used_at,) if row_exists else None
    conn.cursor.return_value = cur
    return conn


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClassifyDamagePure:
    def test_returns_labeled_dict(self):
        result = classify_damage("ev-001")
        assert isinstance(result, Labeled)
        assert isinstance(result.value, dict)

    def test_deterministic(self):
        a = classify_damage("ev-determinism-check")
        b = classify_damage("ev-determinism-check")
        assert a.value["damage_label"] == b.value["damage_label"]
        assert a.value["confidence"] == b.value["confidence"]

    def test_evidence_ref_echoed(self):
        ref = "ev-echo-test-abc"
        result = classify_damage(ref)
        assert result.value["evidence_ref"] == ref

    def test_value_has_required_keys(self):
        result = classify_damage("ev-keys")
        assert {"evidence_ref", "damage_label", "confidence"} <= result.value.keys()

    def test_damage_label_is_valid_category(self):
        result = classify_damage("ev-valid-cat")
        assert result.value["damage_label"] in _DAMAGE_LABELS

    def test_confidence_in_range(self):
        result = classify_damage("ev-confidence-range")
        conf = result.value["confidence"]
        assert 0.0 <= conf <= 1.0

    def test_all_eight_labels_reachable(self):
        """Probe enough distinct inputs to hit all 8 damage categories."""
        seen: set[str] = set()
        for i in range(200):
            seen.add(classify_damage(f"probe-{i:04d}").value["damage_label"])
            if len(seen) == len(_DAMAGE_LABELS):
                break
        assert seen == set(_DAMAGE_LABELS), (
            f"Missing labels: {set(_DAMAGE_LABELS) - seen}"
        )

    def test_ifc_label_is_confidential(self):
        result = classify_damage("ev-label-check")
        assert result.label.level == DataLabel.CONFIDENTIAL

    def test_ifc_label_not_untrusted(self):
        result = classify_damage("ev-untrusted-check")
        assert result.label.untrusted is False

    def test_different_refs_may_differ(self):
        """Two distinct refs should not always hash to the same bucket."""
        labels = {classify_damage(f"ev-diff-{i}").value["damage_label"] for i in range(20)}
        assert len(labels) > 1

    def test_confidence_matches_label(self):
        """The returned confidence must match the hardcoded per-label value."""
        from agent_system.tools.implementations.claims_tools import _CONFIDENCE

        result = classify_damage("ev-conf-match")
        expected = _CONFIDENCE[result.value["damage_label"]]
        assert result.value["confidence"] == expected


# ---------------------------------------------------------------------------
# ToolRegistry integration tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def classify_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("classify_damage", classify_damage)
    return r


@pytest.fixture()
def classify_token(orchestrator_km):
    return issue_token(
        orchestrator_km,
        agent_id="claims_processor",
        tool="classify_damage",
        scope={"evidence_ref": "ev-token-001"},
    )


def _invoke_classify(registry, token, orchestrator_km, *, params=None, used_at=None, row_exists=True):
    if params is None:
        params = {"evidence_ref": "ev-token-001"}
    conn = _make_conn(used_at=used_at, row_exists=row_exists)
    with (
        patch("agent_system.tools.registry.append_log", return_value=42) as mock_log,
        patch("agent_system.tools.registry.record_use") as mock_record,
        patch("agent_system.tools.registry._try_record_use"),
    ):
        result = registry.invoke(
            conn,
            token=token,
            calling_agent_id=token.agent_id,
            tool_name="classify_damage",
            params=params,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            trace_id=uuid.uuid4(),
        )
    return result, mock_log, mock_record


@pytest.mark.unit
class TestClassifyDamageRegistry:
    def test_valid_invocation_succeeds(self, classify_registry, classify_token, orchestrator_km):
        result, mock_log, mock_record = _invoke_classify(
            classify_registry, classify_token, orchestrator_km
        )
        assert result
        assert result.log_id == 42
        mock_record.assert_called_once()
        assert mock_log.call_args.kwargs["action"] == "tool_call_ok"

    def test_result_value_is_labeled(self, classify_registry, classify_token, orchestrator_km):
        result, _, _ = _invoke_classify(
            classify_registry, classify_token, orchestrator_km
        )
        assert isinstance(result.value, Labeled)

    def test_result_value_inner_dict_keys(self, classify_registry, classify_token, orchestrator_km):
        result, _, _ = _invoke_classify(
            classify_registry, classify_token, orchestrator_km
        )
        inner = result.value.value
        assert {"evidence_ref", "damage_label", "confidence"} <= inner.keys()

    def test_result_value_ifc_label_confidential(self, classify_registry, classify_token, orchestrator_km):
        result, _, _ = _invoke_classify(
            classify_registry, classify_token, orchestrator_km
        )
        assert result.value.label.level == DataLabel.CONFIDENTIAL

    def test_audit_params_keys_not_values(self, classify_registry, classify_token, orchestrator_km):
        result, mock_log, _ = _invoke_classify(
            classify_registry, classify_token, orchestrator_km
        )
        details = mock_log.call_args.kwargs["details"]
        assert "params_keys" in details
        assert "evidence_ref" not in details
