"""Unit tests for IFC label types and propagation helpers (P3 — task 1.2.4).

Pure logic — no DB, no fixtures.
"""
from __future__ import annotations

import pytest

from agent_system.ifc.labels import DataLabel, Label, Labeled, LabelViolationError
from agent_system.ifc.propagation import join, join_all, taint


# ---------------------------------------------------------------------------
# DataLabel ordering
# ---------------------------------------------------------------------------


class TestDataLabelOrdering:
    def test_order_public_lt_personal(self):
        assert DataLabel.PUBLIC < DataLabel.PERSONAL

    def test_order_personal_lt_confidential(self):
        assert DataLabel.PERSONAL < DataLabel.CONFIDENTIAL

    def test_order_confidential_lt_secret(self):
        assert DataLabel.CONFIDENTIAL < DataLabel.SECRET

    def test_order_public_lt_secret(self):
        assert DataLabel.PUBLIC < DataLabel.SECRET

    def test_order_reflexive(self):
        assert not (DataLabel.PUBLIC < DataLabel.PUBLIC)
        assert not (DataLabel.SECRET < DataLabel.SECRET)

    def test_order_antisymmetric(self):
        assert DataLabel.PUBLIC < DataLabel.PERSONAL
        assert not (DataLabel.PERSONAL < DataLabel.PUBLIC)

    def test_max_returns_secret(self):
        assert max(DataLabel.PUBLIC, DataLabel.SECRET) == DataLabel.SECRET

    def test_max_returns_confidential(self):
        assert max(DataLabel.PERSONAL, DataLabel.CONFIDENTIAL) == DataLabel.CONFIDENTIAL

    def test_eq_same_instance(self):
        assert DataLabel.PUBLIC == DataLabel.PUBLIC

    def test_eq_not_equal(self):
        assert DataLabel.PUBLIC != DataLabel.SECRET

    def test_eq_db_string_match(self):
        assert DataLabel.CONFIDENTIAL == "CONFIDENTIAL"

    def test_eq_db_string_no_match(self):
        assert DataLabel.CONFIDENTIAL != "PUBLIC"

    def test_hash_consistent_with_eq(self):
        assert hash(DataLabel.CONFIDENTIAL) == hash(DataLabel.CONFIDENTIAL)
        assert hash(DataLabel.PUBLIC) != hash(DataLabel.SECRET)

    def test_total_ordering_le_ge(self):
        assert DataLabel.PUBLIC <= DataLabel.PUBLIC
        assert DataLabel.PUBLIC <= DataLabel.SECRET
        assert DataLabel.SECRET >= DataLabel.PUBLIC
        assert DataLabel.SECRET >= DataLabel.SECRET


# ---------------------------------------------------------------------------
# Label
# ---------------------------------------------------------------------------


class TestLabel:
    def test_defaults_to_trusted(self):
        lbl = Label(level=DataLabel.PUBLIC)
        assert lbl.untrusted is False

    def test_str_clean(self):
        lbl = Label(level=DataLabel.CONFIDENTIAL)
        assert str(lbl) == "CONFIDENTIAL"

    def test_str_untrusted(self):
        lbl = Label(level=DataLabel.SECRET, untrusted=True)
        assert str(lbl) == "SECRET+UNTRUSTED"

    def test_frozen_immutable(self):
        lbl = Label(level=DataLabel.PUBLIC)
        with pytest.raises((AttributeError, TypeError)):
            lbl.level = DataLabel.SECRET  # type: ignore[misc]

    def test_equality(self):
        a = Label(level=DataLabel.PERSONAL, untrusted=True)
        b = Label(level=DataLabel.PERSONAL, untrusted=True)
        assert a == b

    def test_inequality_level(self):
        a = Label(level=DataLabel.PUBLIC)
        b = Label(level=DataLabel.PERSONAL)
        assert a != b

    def test_inequality_taint(self):
        a = Label(level=DataLabel.PUBLIC, untrusted=False)
        b = Label(level=DataLabel.PUBLIC, untrusted=True)
        assert a != b

    def test_hashable(self):
        s = {Label(level=DataLabel.PUBLIC), Label(level=DataLabel.PUBLIC)}
        assert len(s) == 1


# ---------------------------------------------------------------------------
# Labeled[T]
# ---------------------------------------------------------------------------


class TestLabeled:
    def test_access_value_and_label(self):
        lbl = Labeled(value=42, label=Label(level=DataLabel.PERSONAL))
        assert lbl.value == 42
        assert lbl.label.level == DataLabel.PERSONAL

    def test_frozen_immutable(self):
        obj = Labeled(value="hello", label=Label(level=DataLabel.PUBLIC))
        with pytest.raises((AttributeError, TypeError)):
            obj.value = "world"  # type: ignore[misc]

    def test_generic_str_type(self):
        obj: Labeled[str] = Labeled(value="pii", label=Label(level=DataLabel.PERSONAL))
        assert isinstance(obj.value, str)

    def test_generic_dict_type(self):
        payload = {"claim_id": "CLM-001"}
        obj: Labeled[dict] = Labeled(
            value=payload, label=Label(level=DataLabel.CONFIDENTIAL)
        )
        assert obj.value["claim_id"] == "CLM-001"


# ---------------------------------------------------------------------------
# join
# ---------------------------------------------------------------------------


class TestJoin:
    def test_same_level_same_taint_idempotent(self):
        lbl = Label(level=DataLabel.PERSONAL)
        assert join(lbl, lbl) == lbl

    def test_join_raises_level(self):
        a = Label(level=DataLabel.PUBLIC)
        b = Label(level=DataLabel.SECRET)
        result = join(a, b)
        assert result.level == DataLabel.SECRET

    def test_join_commutative(self):
        a = Label(level=DataLabel.PERSONAL)
        b = Label(level=DataLabel.CONFIDENTIAL, untrusted=True)
        assert join(a, b) == join(b, a)

    def test_join_associative(self):
        a = Label(level=DataLabel.PUBLIC)
        b = Label(level=DataLabel.PERSONAL, untrusted=True)
        c = Label(level=DataLabel.SECRET)
        assert join(join(a, b), c) == join(a, join(b, c))

    def test_join_taint_propagates(self):
        clean = Label(level=DataLabel.SECRET, untrusted=False)
        untrusted = Label(level=DataLabel.PUBLIC, untrusted=True)
        result = join(clean, untrusted)
        assert result.untrusted is True
        assert result.level == DataLabel.SECRET

    def test_join_both_clean_stays_clean(self):
        a = Label(level=DataLabel.PERSONAL, untrusted=False)
        b = Label(level=DataLabel.CONFIDENTIAL, untrusted=False)
        result = join(a, b)
        assert result.untrusted is False

    def test_join_both_untrusted_stays_untrusted(self):
        a = Label(level=DataLabel.PUBLIC, untrusted=True)
        b = Label(level=DataLabel.PUBLIC, untrusted=True)
        result = join(a, b)
        assert result.untrusted is True

    @pytest.mark.parametrize(
        "a_level, b_level, expected",
        [
            (DataLabel.PUBLIC, DataLabel.PUBLIC, DataLabel.PUBLIC),
            (DataLabel.PUBLIC, DataLabel.PERSONAL, DataLabel.PERSONAL),
            (DataLabel.PUBLIC, DataLabel.CONFIDENTIAL, DataLabel.CONFIDENTIAL),
            (DataLabel.PUBLIC, DataLabel.SECRET, DataLabel.SECRET),
            (DataLabel.PERSONAL, DataLabel.CONFIDENTIAL, DataLabel.CONFIDENTIAL),
            (DataLabel.PERSONAL, DataLabel.SECRET, DataLabel.SECRET),
            (DataLabel.CONFIDENTIAL, DataLabel.SECRET, DataLabel.SECRET),
            (DataLabel.SECRET, DataLabel.SECRET, DataLabel.SECRET),
        ],
    )
    def test_join_level_cross_product(self, a_level, b_level, expected):
        a = Label(level=a_level, untrusted=False)
        b = Label(level=b_level, untrusted=False)
        assert join(a, b).level == expected


# ---------------------------------------------------------------------------
# join_all
# ---------------------------------------------------------------------------


class TestJoinAll:
    def test_empty_returns_public_trusted(self):
        result = join_all([])
        assert result.level == DataLabel.PUBLIC
        assert result.untrusted is False

    def test_single_element_identity(self):
        lbl = Label(level=DataLabel.SECRET, untrusted=True)
        assert join_all([lbl]) == lbl

    def test_multiple_takes_max_level(self):
        labels = [
            Label(level=DataLabel.PUBLIC),
            Label(level=DataLabel.PERSONAL),
            Label(level=DataLabel.CONFIDENTIAL),
        ]
        result = join_all(labels)
        assert result.level == DataLabel.CONFIDENTIAL

    def test_multiple_propagates_taint(self):
        labels = [
            Label(level=DataLabel.SECRET, untrusted=False),
            Label(level=DataLabel.PUBLIC, untrusted=True),
        ]
        result = join_all(labels)
        assert result.level == DataLabel.SECRET
        assert result.untrusted is True

    def test_generator_input(self):
        gen = (Label(level=DataLabel.PERSONAL) for _ in range(3))
        result = join_all(gen)
        assert result.level == DataLabel.PERSONAL


# ---------------------------------------------------------------------------
# taint
# ---------------------------------------------------------------------------


class TestTaint:
    def test_taint_sets_flag(self):
        lbl = Label(level=DataLabel.CONFIDENTIAL, untrusted=False)
        result = taint(lbl)
        assert result.untrusted is True
        assert result.level == DataLabel.CONFIDENTIAL

    def test_taint_idempotent(self):
        lbl = Label(level=DataLabel.SECRET, untrusted=True)
        assert taint(lbl) == taint(taint(lbl))

    def test_taint_does_not_mutate_original(self):
        lbl = Label(level=DataLabel.PUBLIC, untrusted=False)
        _ = taint(lbl)
        assert lbl.untrusted is False

    def test_taint_preserves_level(self):
        for level in DataLabel:
            lbl = Label(level=level, untrusted=False)
            assert taint(lbl).level == level


# ---------------------------------------------------------------------------
# LabelViolationError
# ---------------------------------------------------------------------------


class TestLabelViolationError:
    def test_is_exception(self):
        assert issubclass(LabelViolationError, Exception)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(LabelViolationError, match="too low"):
            raise LabelViolationError("too low")


# ---------------------------------------------------------------------------
# DB serialisation round-trip
# ---------------------------------------------------------------------------


class TestDbStringRoundtrip:
    @pytest.mark.parametrize("value", ["PUBLIC", "PERSONAL", "CONFIDENTIAL", "SECRET"])
    def test_from_db_string(self, value):
        label = DataLabel(value)
        assert label.value == value

    @pytest.mark.parametrize("member", list(DataLabel))
    def test_to_db_string(self, member):
        assert str(Label(level=member)) == member.value
