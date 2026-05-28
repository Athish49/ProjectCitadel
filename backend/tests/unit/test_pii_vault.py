"""Unit tests for the PII vault (task 1.2.7).

All DB interactions are mocked.  Crypto tests use ARGON_TEST params for speed.
"""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import MagicMock, call, patch

import pytest

from agent_system.vault.crypto import (
    ARGON_TEST,
    constant_compare,
    decrypt_field,
    encrypt_field,
    hash_secret,
    verify_secret,
)
from agent_system.vault.verify import MAX_ATTEMPTS, VerifyResult, verify_identity


# ── Fixtures ─────────────────────────────────────────────────────────────────

_PEPPER = b"\x01" * 32
_FIELD_KEY = b"\x02" * 32
_SESSION = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000000")
_CUSTOMER = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000000")
_POLICY = "POL-2024-001"
_DOB = date(1985, 6, 15)
_DOB_ISO = "1985-06-15"
_SSN_LAST4 = "6789"


def _make_conn(
    *,
    fail_count: int = 0,
    customer_row: tuple | None = (_CUSTOMER, _DOB),
    vault_row: tuple | None = (_SSN_LAST4,),
):
    """Build a mock psycopg Connection whose cursor returns canned data."""
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur

    # fetchone() call sequence:
    # 1 → fail_count (COUNT(*))
    # 2 → customer_row (SELECT customers)
    # 3 → vault_row   (SELECT pii_vault)
    cur.fetchone.side_effect = [
        (fail_count,),
        customer_row,
        vault_row,
    ]
    return conn, cur


def _run(
    *,
    ssn_last4: str = _SSN_LAST4,
    dob_iso: str = _DOB_ISO,
    fail_count: int = 0,
    customer_row=(_CUSTOMER, _DOB),
    vault_row=(_SSN_LAST4,),
    policy: str = _POLICY,
    session: uuid.UUID = _SESSION,
) -> tuple[VerifyResult, MagicMock]:
    conn, cur = _make_conn(
        fail_count=fail_count,
        customer_row=customer_row,
        vault_row=vault_row,
    )
    result = verify_identity(
        conn,
        policy_number=policy,
        ssn_last4=ssn_last4,
        dob_iso=dob_iso,
        session_id=session,
    )
    return result, cur


# ── Argon2id hash / verify ────────────────────────────────────────────────────


class TestArgon2id:
    def test_hash_returns_bytes(self):
        stored = hash_secret("secret", _PEPPER, ARGON_TEST)
        assert isinstance(stored, bytes)

    def test_hash_length(self):
        stored = hash_secret("secret", _PEPPER, ARGON_TEST)
        assert len(stored) == ARGON_TEST.salt_length + ARGON_TEST.hash_length

    def test_verify_correct_plaintext(self):
        stored = hash_secret("correct", _PEPPER, ARGON_TEST)
        assert verify_secret("correct", stored, _PEPPER, ARGON_TEST) is True

    def test_verify_wrong_plaintext(self):
        stored = hash_secret("correct", _PEPPER, ARGON_TEST)
        assert verify_secret("wrong", stored, _PEPPER, ARGON_TEST) is False

    def test_verify_wrong_pepper(self):
        stored = hash_secret("correct", _PEPPER, ARGON_TEST)
        assert verify_secret("correct", stored, b"\xff" * 32, ARGON_TEST) is False

    def test_two_hashes_differ(self):
        # Different salts → different stored values (non-deterministic)
        a = hash_secret("same", _PEPPER, ARGON_TEST)
        b = hash_secret("same", _PEPPER, ARGON_TEST)
        assert a != b

    def test_empty_pepper_accepted(self):
        stored = hash_secret("answer", b"", ARGON_TEST)
        assert verify_secret("answer", stored, b"", ARGON_TEST) is True

    def test_truncated_stored_returns_false(self):
        stored = hash_secret("x", _PEPPER, ARGON_TEST)
        assert verify_secret("x", stored[:5], _PEPPER, ARGON_TEST) is False

    def test_ssn_normalised_to_digits(self):
        # store_pii strips dashes before hashing; we test that the same
        # normalised value round-trips through crypto
        raw = "123-45-6789"
        normalised = "".join(c for c in raw if c.isdigit())
        stored = hash_secret(normalised, _PEPPER, ARGON_TEST)
        assert verify_secret(normalised, stored, _PEPPER, ARGON_TEST) is True
        assert verify_secret(raw, stored, _PEPPER, ARGON_TEST) is False


# ── AES-256-GCM encrypt / decrypt ────────────────────────────────────────────


class TestAesGcm:
    def test_roundtrip(self):
        ct, iv = encrypt_field("DL1234567", _FIELD_KEY)
        assert decrypt_field(ct, iv, _FIELD_KEY) == "DL1234567"

    def test_ciphertext_differs_from_plaintext(self):
        ct, _ = encrypt_field("hello", _FIELD_KEY)
        assert ct != b"hello"

    def test_two_encryptions_differ(self):
        ct1, iv1 = encrypt_field("hello", _FIELD_KEY)
        ct2, iv2 = encrypt_field("hello", _FIELD_KEY)
        assert ct1 != ct2  # different nonces

    def test_wrong_key_raises(self):
        ct, iv = encrypt_field("data", _FIELD_KEY)
        with pytest.raises(ValueError):
            decrypt_field(ct, iv, b"\x00" * 32)

    def test_tampered_ciphertext_raises(self):
        ct, iv = encrypt_field("data", _FIELD_KEY)
        tampered = bytes([ct[0] ^ 0xFF]) + ct[1:]
        with pytest.raises(ValueError):
            decrypt_field(tampered, iv, _FIELD_KEY)

    def test_wrong_key_length_raises_on_encrypt(self):
        with pytest.raises(ValueError):
            encrypt_field("data", b"\x00" * 16)

    def test_wrong_key_length_raises_on_decrypt(self):
        ct, iv = encrypt_field("data", _FIELD_KEY)
        with pytest.raises(ValueError):
            decrypt_field(ct, iv, b"\x00" * 16)

    def test_empty_plaintext_roundtrip(self):
        ct, iv = encrypt_field("", _FIELD_KEY)
        assert decrypt_field(ct, iv, _FIELD_KEY) == ""

    def test_unicode_roundtrip(self):
        ct, iv = encrypt_field("José García", _FIELD_KEY)
        assert decrypt_field(ct, iv, _FIELD_KEY) == "José García"


# ── constant_compare ──────────────────────────────────────────────────────────


class TestConstantCompare:
    def test_equal(self):
        assert constant_compare("1234", "1234") is True

    def test_not_equal(self):
        assert constant_compare("1234", "1235") is False

    def test_empty(self):
        assert constant_compare("", "") is True

    def test_different_lengths(self):
        assert constant_compare("123", "1234") is False


# ── verify_identity — happy path ──────────────────────────────────────────────


class TestVerifyIdentitySuccess:
    def test_correct_credentials_returns_verified(self):
        result, _ = _run()
        assert result.verified is True

    def test_outcome_success(self):
        result, _ = _run()
        assert result.outcome == "SUCCESS"

    def test_attempts_remaining_full_on_first_try(self):
        result, _ = _run(fail_count=0)
        assert result.attempts_remaining == MAX_ATTEMPTS

    def test_attempts_remaining_decremented_after_prior_failure(self):
        result, _ = _run(fail_count=1)
        assert result.attempts_remaining == MAX_ATTEMPTS - 1

    def test_inserts_success_attempt(self):
        _, cur = _run()
        insert_calls = [
            c for c in cur.execute.call_args_list
            if "INSERT INTO identity_attempts" in str(c)
        ]
        assert len(insert_calls) == 1
        assert "SUCCESS" in str(insert_calls[0])

    def test_no_security_event_on_success(self):
        _, cur = _run()
        sec_calls = [
            c for c in cur.execute.call_args_list
            if "security_events" in str(c)
        ]
        assert sec_calls == []


# ── verify_identity — FAIL_MATCH ─────────────────────────────────────────────


class TestVerifyIdentityFailMatch:
    def test_wrong_ssn_last4_not_verified(self):
        result, _ = _run(ssn_last4="0000")
        assert not result.verified
        assert result.outcome == "FAIL_MATCH"

    def test_wrong_dob_not_verified(self):
        result, _ = _run(dob_iso="2000-01-01")
        assert not result.verified
        assert result.outcome == "FAIL_MATCH"

    def test_attempts_remaining_decremented(self):
        result, _ = _run(ssn_last4="0000", fail_count=1)
        assert result.attempts_remaining == MAX_ATTEMPTS - 2

    def test_inserts_fail_match_attempt(self):
        _, cur = _run(ssn_last4="0000")
        insert_calls = [
            c for c in cur.execute.call_args_list
            if "INSERT INTO identity_attempts" in str(c)
        ]
        assert len(insert_calls) == 1
        assert "FAIL_MATCH" in str(insert_calls[0])

    def test_security_event_written_on_fail(self):
        _, cur = _run(ssn_last4="0000")
        sec_calls = [
            c for c in cur.execute.call_args_list
            if "security_events" in str(c)
        ]
        assert len(sec_calls) == 1

    def test_policy_not_found_returns_fail_match(self):
        result, _ = _run(customer_row=None)
        assert result.outcome == "FAIL_MATCH"
        assert not result.verified

    def test_vault_row_missing_returns_fail_match(self):
        result, _ = _run(vault_row=None)
        assert result.outcome == "FAIL_MATCH"
        assert not result.verified

    def test_attempts_remaining_zero_at_last_chance(self):
        result, _ = _run(ssn_last4="0000", fail_count=MAX_ATTEMPTS - 1)
        assert result.attempts_remaining == 0


# ── verify_identity — LOCKOUT ─────────────────────────────────────────────────


class TestVerifyIdentityLockout:
    def test_locked_out_after_max_failures(self):
        result, _ = _run(fail_count=MAX_ATTEMPTS)
        assert result.outcome == "LOCKOUT"
        assert not result.verified

    def test_lockout_attempts_remaining_zero(self):
        result, _ = _run(fail_count=MAX_ATTEMPTS)
        assert result.attempts_remaining == 0

    def test_lockout_does_not_query_vault(self):
        _, cur = _run(fail_count=MAX_ATTEMPTS)
        vault_calls = [
            c for c in cur.execute.call_args_list
            if "pii_vault" in str(c)
        ]
        assert vault_calls == []

    def test_lockout_does_not_query_customers(self):
        _, cur = _run(fail_count=MAX_ATTEMPTS)
        cust_calls = [
            c for c in cur.execute.call_args_list
            if "customers" in str(c) and "SELECT" in str(c)
        ]
        assert cust_calls == []

    def test_lockout_inserts_lockout_attempt(self):
        _, cur = _run(fail_count=MAX_ATTEMPTS)
        insert_calls = [
            c for c in cur.execute.call_args_list
            if "INSERT INTO identity_attempts" in str(c)
        ]
        assert len(insert_calls) == 1
        assert "LOCKOUT" in str(insert_calls[0])

    def test_lockout_writes_security_event(self):
        _, cur = _run(fail_count=MAX_ATTEMPTS)
        sec_calls = [
            c for c in cur.execute.call_args_list
            if "security_events" in str(c)
        ]
        assert len(sec_calls) == 1
        assert "identity_lockout" in str(sec_calls[0])

    def test_lockout_at_exactly_max_plus_one(self):
        # MAX_ATTEMPTS + 1 prior failures: still LOCKOUT
        result, _ = _run(fail_count=MAX_ATTEMPTS + 1)
        assert result.outcome == "LOCKOUT"

    def test_third_attempt_still_checked(self):
        # fail_count == MAX_ATTEMPTS - 1 → still in the genuine check path
        result, _ = _run(ssn_last4=_SSN_LAST4, dob_iso=_DOB_ISO, fail_count=MAX_ATTEMPTS - 1)
        assert result.outcome == "SUCCESS"


# ── DOB format tolerance ──────────────────────────────────────────────────────


class TestDobFormats:
    def test_iso_format_accepted(self):
        result, _ = _run(dob_iso="1985-06-15")
        assert result.verified is True

    def test_malformed_dob_does_not_raise(self):
        # verify_identity must never raise
        result, _ = _run(dob_iso="not-a-date")
        assert result.outcome == "FAIL_MATCH"
        assert not result.verified


# ── Error resilience ──────────────────────────────────────────────────────────


class TestErrorResilience:
    def test_db_exception_returns_fail_match(self):
        conn = MagicMock()
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur
        cur.execute.side_effect = RuntimeError("DB exploded")

        result = verify_identity(
            conn,
            policy_number=_POLICY,
            ssn_last4=_SSN_LAST4,
            dob_iso=_DOB_ISO,
            session_id=_SESSION,
        )
        assert not result.verified
        assert result.outcome == "FAIL_MATCH"
