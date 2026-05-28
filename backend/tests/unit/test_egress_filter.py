"""Unit tests for egress output filter (P10 — task 1.2.5).

All DB interactions are mocked.  Pure-logic helpers (patterns, allowlist)
are tested independently before integration through filter_output().
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, call, patch

import pytest

from agent_system.egress.allowlist import ALLOWED_HOSTS, strip_urls
from agent_system.egress.filter import (
    MAX_OUTPUT_CHARS,
    REFUSAL_MESSAGE,
    FilterResult,
    filter_output,
)
from agent_system.egress.patterns import _luhn_check, find_pii
from agent_system.ifc.labels import DataLabel, Label


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CLEAN_LABEL = Label(level=DataLabel.PUBLIC)
_PERSONAL_LABEL = Label(level=DataLabel.PERSONAL)
_CONFIDENTIAL_LABEL = Label(level=DataLabel.CONFIDENTIAL)
_SECRET_LABEL = Label(level=DataLabel.SECRET)

# Stripe test card — passes Luhn
_VALID_CARD = "4242424242424242"
# Spaced variant of same number
_VALID_CARD_SPACED = "4242 4242 4242 4242"
# Known-invalid Luhn
_INVALID_CARD = "1234567890123456"


def _make_conn():
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur
    return conn


def _run(text: str, label: Label, *, log_return=1):
    conn = _make_conn()
    with patch(
        "agent_system.egress.filter.append_log", return_value=log_return
    ) as mock_log:
        result = filter_output(
            conn,
            text=text,
            source_label=label,
            calling_agent_id="test_agent",
            trace_id=uuid.uuid4(),
        )
    return result, mock_log


# ---------------------------------------------------------------------------
# FilterResult
# ---------------------------------------------------------------------------


class TestFilterResult:
    def test_ok_is_truthy(self):
        r = FilterResult(ok=True, output="hi")
        assert r

    def test_blocked_is_falsy(self):
        r = FilterResult(ok=False, output=REFUSAL_MESSAGE)
        assert not r

    def test_defaults(self):
        r = FilterResult(ok=True, output="x")
        assert r.violations == []
        assert r.log_ids == []


# ---------------------------------------------------------------------------
# Luhn check
# ---------------------------------------------------------------------------


class TestLuhn:
    def test_valid_stripe_card(self):
        assert _luhn_check(_VALID_CARD) is True

    def test_valid_card_with_spaces(self):
        assert _luhn_check(_VALID_CARD_SPACED) is True

    def test_valid_card_with_dashes(self):
        assert _luhn_check("4242-4242-4242-4242") is True

    def test_known_invalid(self):
        assert _luhn_check(_INVALID_CARD) is False

    def test_too_short(self):
        assert _luhn_check("123456789012") is False  # 12 digits

    def test_too_long(self):
        assert _luhn_check("1" * 20) is False  # 20 digits


# ---------------------------------------------------------------------------
# PII patterns
# ---------------------------------------------------------------------------


class TestFindPii:
    def test_ssn_with_dashes(self):
        assert "ssn" in find_pii("SSN: 123-45-6789")

    def test_ssn_with_spaces(self):
        assert "ssn" in find_pii("social 123 45 6789 end")

    def test_no_ssn_plain_digits(self):
        # 9-digit plain number without separators should NOT trigger SSN
        assert "ssn" not in find_pii("reference 123456789 ok")

    def test_phone_dash_format(self):
        assert "phone" in find_pii("call 555-867-5309 now")

    def test_phone_paren_format(self):
        assert "phone" in find_pii("reach us at (800) 123-4567")

    def test_phone_dot_format(self):
        assert "phone" in find_pii("number is 555.123.4567")

    def test_valid_credit_card_found(self):
        assert "credit_card" in find_pii(f"card {_VALID_CARD} used")

    def test_valid_credit_card_spaced_found(self):
        assert "credit_card" in find_pii(f"pay with {_VALID_CARD_SPACED} please")

    def test_invalid_luhn_not_found(self):
        assert "credit_card" not in find_pii(f"ref {_INVALID_CARD} end")

    def test_clean_text_no_pii(self):
        assert find_pii("Your claim CLM-001 is under review.") == []

    def test_multiple_pii_types_all_reported(self):
        text = f"SSN 123-45-6789 and card {_VALID_CARD}"
        result = find_pii(text)
        assert "ssn" in result
        assert "credit_card" in result


# ---------------------------------------------------------------------------
# URL stripping
# ---------------------------------------------------------------------------


class TestStripUrls:
    def test_allowed_url_passes(self):
        text = "See https://docs.secureclaim.example/faq"
        out, stripped = strip_urls(text)
        assert stripped == []
        assert out == text

    def test_allowed_status_url_passes(self):
        text = "Check https://status.secureclaim.example"
        out, stripped = strip_urls(text)
        assert stripped == []

    def test_subdomain_of_allowed_passes(self):
        text = "https://sub.docs.secureclaim.example/page"
        out, stripped = strip_urls(text)
        assert stripped == []

    def test_disallowed_url_stripped(self):
        text = "data at https://evil.example.com/leak"
        out, stripped = strip_urls(text)
        assert "https://evil.example.com/leak" in stripped
        assert "[external link removed]" in out
        assert "evil.example.com" not in out

    def test_typosquat_stripped(self):
        text = "see https://evil.secureclaim.example/steal"
        _, stripped = strip_urls(text)
        assert stripped  # not in allowlist despite containing secureclaim.example

    def test_multiple_urls_mixed(self):
        text = (
            "docs at https://docs.secureclaim.example/x "
            "and https://attacker.io/exfil"
        )
        out, stripped = strip_urls(text)
        assert len(stripped) == 1
        assert "attacker.io" in stripped[0]
        assert "docs.secureclaim.example" in out

    def test_no_urls_unchanged(self):
        text = "no links here"
        out, stripped = strip_urls(text)
        assert out == text
        assert stripped == []

    def test_url_no_parseable_host_stripped(self):
        # https:///path matches regex but has no netloc; hostname is None → strip
        text = "go to https:///exfil now"
        _, stripped = strip_urls(text)
        assert stripped  # no hostname → not allowed → stripped


# ---------------------------------------------------------------------------
# filter_output — SECRET block
# ---------------------------------------------------------------------------


class TestSecretBlock:
    def test_secret_label_blocked(self):
        result, _ = _run("some sensitive data", _SECRET_LABEL)
        assert not result
        assert result.output == REFUSAL_MESSAGE
        assert "secret_label" in result.violations

    def test_secret_logs_security_event(self):
        _, mock_log = _run("data", _SECRET_LABEL)
        mock_log.assert_called_once()
        kw = mock_log.call_args.kwargs
        assert kw["action"] == "egress_blocked_secret"
        assert kw["security_event"] is True

    def test_secret_short_circuits_no_pii_check(self):
        # Even if there's PII, SECRET kills first — only one append_log call
        text = f"SSN 123-45-6789 card {_VALID_CARD}"
        _, mock_log = _run(text, _SECRET_LABEL)
        mock_log.assert_called_once()
        kw = mock_log.call_args.kwargs
        assert kw["action"] == "egress_blocked_secret"

    def test_non_secret_label_not_blocked_by_label(self):
        result, _ = _run("hello world", _CONFIDENTIAL_LABEL)
        assert result  # CONFIDENTIAL should not block on label alone
        assert result.output == "hello world"

    def test_untrusted_non_secret_not_blocked(self):
        # UNTRUSTED taint alone does not trigger the SECRET kill switch
        lbl = Label(level=DataLabel.CONFIDENTIAL, untrusted=True)
        result, _ = _run("clean text", lbl)
        assert result


# ---------------------------------------------------------------------------
# filter_output — URL stripping
# ---------------------------------------------------------------------------


class TestEgressUrlStripping:
    def test_disallowed_url_stripped_in_output(self):
        text = "see https://evil.example.com/data"
        result, _ = _run(text, _CLEAN_LABEL)
        assert result  # URL strip doesn't block
        assert "[external link removed]" in result.output
        assert "evil.example.com" not in result.output

    def test_url_violation_logged_as_security_event(self):
        text = "https://attacker.io/x"
        _, mock_log = _run(text, _CLEAN_LABEL)
        kw = mock_log.call_args.kwargs
        assert kw["action"] == "egress_url_stripped"
        assert kw["security_event"] is True

    def test_multiple_url_violations_each_logged(self):
        text = "a https://evil1.com b https://evil2.com"
        _, mock_log = _run(text, _CLEAN_LABEL)
        assert mock_log.call_count == 2
        actions = [c.kwargs["action"] for c in mock_log.call_args_list]
        assert all(a == "egress_url_stripped" for a in actions)

    def test_allowed_url_no_log(self):
        text = "https://docs.secureclaim.example/help"
        _, mock_log = _run(text, _CLEAN_LABEL)
        mock_log.assert_not_called()

    def test_url_violation_in_violations_list(self):
        bad = "https://evil.example.com/exfil"
        result, _ = _run(f"here: {bad}", _CLEAN_LABEL)
        assert any("url:" in v for v in result.violations)


# ---------------------------------------------------------------------------
# filter_output — PII blocking
# ---------------------------------------------------------------------------


class TestEgressPiiBlocking:
    def test_ssn_blocks_response(self):
        result, _ = _run("Your SSN is 123-45-6789", _CLEAN_LABEL)
        assert not result
        assert result.output == REFUSAL_MESSAGE

    def test_phone_blocks_response(self):
        result, _ = _run("call (555) 123-4567 now", _CLEAN_LABEL)
        assert not result

    def test_valid_card_blocks_response(self):
        result, _ = _run(f"card number: {_VALID_CARD}", _CLEAN_LABEL)
        assert not result

    def test_invalid_luhn_card_does_not_block(self):
        result, _ = _run(f"ref: {_INVALID_CARD}", _CLEAN_LABEL)
        assert result

    def test_pii_block_logs_security_event(self):
        _, mock_log = _run("SSN 123-45-6789", _CLEAN_LABEL)
        kw = mock_log.call_args.kwargs
        assert kw["action"] == "egress_blocked_pii"
        assert kw["security_event"] is True

    def test_pii_block_details_contain_type(self):
        _, mock_log = _run("SSN 123-45-6789", _CLEAN_LABEL)
        kw = mock_log.call_args.kwargs
        assert "ssn" in kw["details"]["pii_types"]

    def test_pii_violation_in_violations_list(self):
        result, _ = _run("SSN 123-45-6789", _CLEAN_LABEL)
        assert any(v.startswith("pii:") for v in result.violations)


# ---------------------------------------------------------------------------
# filter_output — length cap
# ---------------------------------------------------------------------------


class TestLengthCap:
    def test_long_text_truncated(self):
        text = "x" * (MAX_OUTPUT_CHARS + 100)
        result, _ = _run(text, _CLEAN_LABEL)
        assert result  # truncation doesn't block
        assert len(result.output) == MAX_OUTPUT_CHARS

    def test_truncation_logged_not_security_event(self):
        text = "y" * (MAX_OUTPUT_CHARS + 1)
        _, mock_log = _run(text, _CLEAN_LABEL)
        mock_log.assert_called_once()
        kw = mock_log.call_args.kwargs
        assert kw["action"] == "egress_truncated"
        assert kw["security_event"] is False

    def test_short_text_not_truncated(self):
        text = "short"
        result, mock_log = _run(text, _CLEAN_LABEL)
        assert result.output == text
        mock_log.assert_not_called()

    def test_exact_limit_not_truncated(self):
        text = "z" * MAX_OUTPUT_CHARS
        result, mock_log = _run(text, _CLEAN_LABEL)
        assert len(result.output) == MAX_OUTPUT_CHARS
        mock_log.assert_not_called()

    def test_truncation_in_violations_list(self):
        result, _ = _run("a" * (MAX_OUTPUT_CHARS + 1), _CLEAN_LABEL)
        assert "truncated" in result.violations


# ---------------------------------------------------------------------------
# filter_output — stacked violations
# ---------------------------------------------------------------------------


class TestStackedViolations:
    def test_url_then_pii_both_logged(self):
        # URL stripped first; PII found in remaining text → block
        text = f"go https://evil.com then SSN 123-45-6789"
        result, mock_log = _run(text, _CLEAN_LABEL)
        assert not result  # PII blocks
        actions = [c.kwargs["action"] for c in mock_log.call_args_list]
        assert "egress_url_stripped" in actions
        assert "egress_blocked_pii" in actions

    def test_url_strip_plus_truncation(self):
        # URL stripped (ok), then text is long → truncated (ok)
        bad_url = "https://evil.com/x"
        text = bad_url + " " + "a" * (MAX_OUTPUT_CHARS + 50)
        result, mock_log = _run(text, _CLEAN_LABEL)
        assert result  # both are non-blocking
        actions = [c.kwargs["action"] for c in mock_log.call_args_list]
        assert "egress_url_stripped" in actions
        assert "egress_truncated" in actions

    def test_clean_text_no_log_no_violations(self):
        result, mock_log = _run("Your claim is approved.", _CLEAN_LABEL)
        assert result
        assert result.output == "Your claim is approved."
        assert result.violations == []
        mock_log.assert_not_called()
