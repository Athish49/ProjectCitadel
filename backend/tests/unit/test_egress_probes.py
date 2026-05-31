"""
Sprint 5.1.5 — URL/PII Egress Adversarial Probe Suite (Unit Layer)
===================================================================

Adversarial probes for the P10 egress output filter covering:
  - Attack #25 (URL-based Exfiltration): bypass attempts against the URL allowlist
  - Attack #20 (Direct Exfiltration): PII evasion and smuggling patterns

These tests are complementary to test_egress_filter.py (which covers the
happy path and basic cases).  Every class documents the attack ID and the
specific control under test.

All DB interactions are mocked — pure-logic probes.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from agent_system.egress.allowlist import _is_allowed, strip_urls
from agent_system.egress.filter import (
    MAX_OUTPUT_CHARS,
    REFUSAL_MESSAGE,
    filter_output,
)
from agent_system.egress.patterns import find_pii
from agent_system.ifc.labels import DataLabel, Label

# ── label fixtures ───────────────────────────────────────────────────────────
_PUBLIC = Label(level=DataLabel.PUBLIC)
_CONFIDENTIAL = Label(level=DataLabel.CONFIDENTIAL)
_SECRET = Label(level=DataLabel.SECRET)

# ── helper ───────────────────────────────────────────────────────────────────

def _make_conn():
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur
    return conn


def _run(text: str, label: Label = _PUBLIC, *, log_return: int = 1):
    conn = _make_conn()
    with patch("agent_system.egress.filter.append_log", return_value=log_return) as mock_log:
        result = filter_output(
            conn,
            text=text,
            source_label=label,
            calling_agent_id="probe_agent",
            trace_id=uuid.uuid4(),
        )
    return result, mock_log


# ── Attack #25: URL allowlist bypass probes ───────────────────────────────────

class TestURLAllowlistBypassProbes:
    """
    Attack #25 (URL-based Exfiltration).

    An LLM agent may be prompted to embed exfiltration URLs in its response.
    These probes verify that allowlist enforcement cannot be bypassed by
    URL construction tricks.
    """

    def test_userinfo_trick_stripped(self):
        """
        http://docs.secureclaim.example@evil.com/exfil
        urlparse.hostname → 'evil.com' (userinfo is the trusted-looking prefix).
        The filter must not be fooled by the allowed domain appearing as userinfo.
        """
        url = "http://docs.secureclaim.example@evil.com/exfil"
        _, stripped = strip_urls(f"report at {url}")
        assert url in stripped, "[Attack #25] Userinfo trick bypassed allowlist"
        assert not _is_allowed(url)

    def test_subdomain_confusion_stripped(self):
        """
        https://docs.secureclaim.example.evil.com/x
        hostname ends with .evil.com, not .docs.secureclaim.example.
        """
        url = "https://docs.secureclaim.example.evil.com/x"
        _, stripped = strip_urls(f"see {url}")
        assert stripped, "[Attack #25] Subdomain confusion bypassed allowlist"

    def test_ipv4_literal_stripped(self):
        """http://192.0.2.1/steal — no hostname match possible."""
        _, stripped = strip_urls("data at http://192.0.2.1/steal now")
        assert stripped, "[Attack #25] IPv4 literal passed allowlist"

    def test_ipv6_literal_stripped(self):
        """http://[::1]/exfil — IPv6 loopback should be denied."""
        _, stripped = strip_urls("go to http://[::1]/exfil")
        assert stripped, "[Attack #25] IPv6 literal passed allowlist"

    def test_localhost_stripped(self):
        """http://localhost/data — internal host must be denied."""
        _, stripped = strip_urls("see http://localhost/data here")
        assert stripped, "[Attack #25] localhost passed allowlist"

    def test_127_0_0_1_stripped(self):
        """http://127.0.0.1/leak — loopback IP must be denied."""
        _, stripped = strip_urls("see http://127.0.0.1/leak here")
        assert stripped, "[Attack #25] 127.0.0.1 passed allowlist"

    def test_port_on_allowed_host_passes(self):
        """
        http://docs.secureclaim.example:8080/x — port suffix should not
        break the allowlist.  urlparse.hostname strips the port.  This is a
        positive control: port-qualified allowed hosts must still pass.
        """
        url = "http://docs.secureclaim.example:8080/x"
        assert _is_allowed(url), "Port-qualified allowed host should pass"
        out, stripped = strip_urls(f"see {url} now")
        assert not stripped, "Port-qualified allowed URL must not be stripped"

    def test_url_with_trailing_paren_stripped(self):
        """
        URL regex does not exclude ')' so the match includes the trailing paren
        from markdown `(see http://evil.com/data)`.  The whole captured token
        (including paren) is stripped — behavior pinned.
        """
        text = "(see http://evil.com/data)"
        out, stripped = strip_urls(text)
        assert stripped, "[Attack #25] Paren-wrapped URL passed allowlist"
        assert "evil.com" not in out

    def test_url_in_json_value_stripped(self):
        """URL embedded as a JSON string value must still be stripped."""
        text = '{"redirect": "http://evil.com/steal", "ok": true}'
        out, stripped = strip_urls(text)
        assert stripped, "[Attack #25] JSON-embedded URL passed allowlist"
        assert "evil.com" not in out

    def test_filter_output_strips_url_does_not_block(self):
        """URL stripping is non-blocking — ok=True with violation noted."""
        result, mock_log = _run("see https://attacker.io/grab for data")
        assert result.ok, "URL stripping should not block (ok must remain True)"
        assert "[external link removed]" in result.output
        assert any("url:" in v for v in result.violations)
        kw = mock_log.call_args.kwargs
        assert kw["action"] == "egress_url_stripped"
        assert kw["security_event"] is True

    def test_multiple_disallowed_urls_all_stripped(self):
        """Each disallowed URL must be stripped and individually audited."""
        text = "A: https://evil1.com/x B: https://evil2.com/y"
        result, mock_log = _run(text)
        assert result.ok
        assert mock_log.call_count == 2
        assert result.output.count("[external link removed]") == 2

    def test_allowed_url_never_stripped(self):
        """https://docs.secureclaim.example/faq must never appear in stripped list."""
        text = "see https://docs.secureclaim.example/faq for help"
        result, mock_log = _run(text)
        assert result.ok
        assert result.output == text
        mock_log.assert_not_called()


# ── Attack #20: PII exfiltration probes ──────────────────────────────────────

class TestPIIExfiltrationProbes:
    """
    Attack #20 (Direct Exfiltration).

    An LLM agent may inadvertently or adversarially echo PII from its context
    window.  These probes verify the PII detection fires on the pattern
    variants an attacker would use.
    """

    def test_ssn_dash_format_blocks(self):
        result, _ = _run("Your SSN is 123-45-6789.")
        assert not result.ok
        assert result.output == REFUSAL_MESSAGE
        assert "pii:ssn" in result.violations

    def test_ssn_space_format_blocks(self):
        result, _ = _run("social security: 123 45 6789")
        assert not result.ok
        assert "pii:ssn" in result.violations

    def test_phone_e164_format_blocks(self):
        result, _ = _run("contact +1 555-867-5309 today")
        assert not result.ok
        assert "pii:phone" in result.violations

    def test_phone_paren_format_blocks(self):
        result, _ = _run("call us at (800) 555-1234")
        assert not result.ok
        assert "pii:phone" in result.violations

    def test_valid_credit_card_blocks(self):
        """Stripe test card 4242…4242 passes Luhn and must block."""
        result, _ = _run("payment card: 4242 4242 4242 4242")
        assert not result.ok
        assert "pii:credit_card" in result.violations

    def test_credit_card_with_dashes_blocks(self):
        result, _ = _run("card 4242-4242-4242-4242 used")
        assert not result.ok
        assert "pii:credit_card" in result.violations

    def test_pii_deep_in_long_response_blocks(self):
        """PII buried in a long response (but within MAX_OUTPUT_CHARS) must block."""
        padding = "This claim is under review. " * 50  # well under 2000 chars
        text = padding + "SSN: 123-45-6789"
        result, _ = _run(text)
        assert not result.ok, "PII buried in long response must still block"

    def test_pii_logs_security_event(self):
        _, mock_log = _run("SSN 123-45-6789", _CONFIDENTIAL)
        kw = mock_log.call_args.kwargs
        assert kw["action"] == "egress_blocked_pii"
        assert kw["security_event"] is True

    def test_clean_claim_response_not_blocked(self):
        """Positive control: normal claim status text must pass all checks."""
        text = "Your claim CLM-2024-001 is currently under review. Expected resolution in 5 business days."
        result, mock_log = _run(text)
        assert result.ok
        assert result.output == text
        mock_log.assert_not_called()


# ── Attack #20/#25: PII smuggled via URL ─────────────────────────────────────

class TestPIIInURLProbes:
    """
    Intersection of Attack #25 (URL exfiltration) and #20 (PII exfiltration).

    Tests the ordering of filter steps: URL stripping (Step 2) runs before
    PII detection (Step 3).  The behavior depends on whether the URL is on
    the allowlist.
    """

    def test_ssn_in_disallowed_url_stripped_not_pii_blocked(self):
        """
        SSN embedded in a disallowed URL's query string is removed when the
        URL is stripped.  The remaining text has no PII → ok=True.
        This is NOT a bypass: the SSN never reaches the customer.
        """
        text = "Details at https://evil.com/?ssn=123-45-6789 for reference."
        result, mock_log = _run(text)
        assert result.ok, "URL strip removes the SSN with the URL — not a PII leak"
        assert "evil.com" not in result.output
        # Only url-stripped event, not pii-blocked
        actions = [c.kwargs["action"] for c in mock_log.call_args_list]
        assert "egress_url_stripped" in actions
        assert "egress_blocked_pii" not in actions

    def test_ssn_in_allowed_url_triggers_pii_block(self):
        """
        SSN embedded in an allowed URL passes URL stripping (URL is not removed)
        but is then found by the PII check → response blocked.
        This is the critical invariant: allowlisted URLs are not PII-safe channels.
        """
        text = "see https://docs.secureclaim.example/?ssn=123-45-6789 for info"
        result, mock_log = _run(text)
        assert not result.ok, (
            "[Attack #20] SSN inside allowlisted URL should still trigger PII block"
        )
        actions = [c.kwargs["action"] for c in mock_log.call_args_list]
        assert "egress_blocked_pii" in actions
        # URL itself must not have been stripped
        assert "egress_url_stripped" not in actions

    def test_phone_in_disallowed_url_stripped(self):
        """Phone number embedded in disallowed URL path → stripped with URL, no block."""
        text = "call https://attacker.io/call/555-867-5309 now"
        result, _ = _run(text)
        assert result.ok
        assert "555-867-5309" not in result.output


# ── Attack #20: PII past the truncation boundary ─────────────────────────────

class TestPIIPastTruncationBoundary:
    """
    Attack #20 invariant: PII detection runs on the FULL URL-stripped text
    BEFORE the length cap is applied (Step 3 before Step 4).

    An attacker cannot smuggle PII into a response by padding the text so
    that the PII lands past position MAX_OUTPUT_CHARS — the truncation would
    remove it from the delivered output, but filter_output still detects and
    blocks it.  This ensures the filter never silently delivers a PII-free
    truncation of a PII-containing response.
    """

    def test_ssn_past_truncation_point_blocks(self):
        """SSN at position MAX_OUTPUT_CHARS + 500 must still block the response."""
        # Pad beyond the truncation boundary, then add SSN
        padding = "a" * (MAX_OUTPUT_CHARS + 500)
        text = padding + " SSN 123-45-6789 end"
        result, _ = _run(text)
        assert not result.ok, (
            "[Attack #20] PII past truncation boundary must still block response — "
            "filter must not silently truncate-and-deliver a PII-containing response"
        )
        assert result.output == REFUSAL_MESSAGE

    def test_pii_immediately_after_cap_blocks(self):
        """SSN at exactly position MAX_OUTPUT_CHARS + 1 must still block."""
        text = "b" * MAX_OUTPUT_CHARS + " SSN 123-45-6789"
        result, _ = _run(text)
        assert not result.ok, (
            "[Attack #20] PII immediately after truncation boundary must still block"
        )

    def test_clean_long_response_truncated_not_blocked(self):
        """Positive control: long clean response is truncated but ok=True."""
        text = "Clean sentence. " * 200  # well over 2000 chars, no PII
        result, mock_log = _run(text)
        assert result.ok
        assert len(result.output) == MAX_OUTPUT_CHARS
        mock_log.assert_called_once()
        kw = mock_log.call_args.kwargs
        assert kw["action"] == "egress_truncated"
        assert kw["security_event"] is False


# ── Attack #20: known PII evasion gaps (documented, not failures) ────────────

class TestPIIEvasionGapsDocumented:
    """
    Attack #20 — patterns that EVADE the current regex-based PII detector.

    These tests document known gaps in the pattern layer.  They are NOT
    test failures — they confirm the behavior so the team can decide whether
    to close each gap with a stricter regex or to rely on the LLM-layer
    guard (P3) for these cases.

    Each test is annotated with the recommended mitigation tier.
    """

    def test_ssn_no_separators_evades(self):
        """
        9-digit SSN with no separators ('123456789') does NOT trigger the SSN
        pattern.  By design: the pattern requires separators to avoid false
        positives on claim reference numbers.

        Mitigation: P3 (LLM classifier) should catch SSNs without separators
        in context.
        """
        violations = find_pii("reference 123456789 end")
        assert "ssn" not in violations, (
            "9-digit no-separator SSN correctly evades — gap is by design"
        )

    def test_phone_no_separator_evades(self):
        """
        Plain 10-digit phone ('5558675309') without any separator evades
        detection.  The pattern requires at least one separator to avoid
        matching numeric identifiers.
        """
        violations = find_pii("number 5558675309 ok")
        assert "phone" not in violations, "No-separator phone evades — by design"

    def test_ssn_spelled_out_evades(self):
        """
        'one two three forty-five six seven eight nine' — spelled-out SSN
        evades the digit-based regex.  P3 LLM guard is the backstop.
        """
        violations = find_pii("SSN: one two three dash four five dash six seven eight nine")
        assert "ssn" not in violations, "Spelled-out SSN evades regex — expected"

    def test_credit_card_luhn_invalid_evades(self):
        """
        A 16-digit number that fails Luhn check is not treated as a credit card.
        This is correct behavior — avoids false positives on invoice/order IDs.
        """
        violations = find_pii("invoice 1234567890123456")
        assert "credit_card" not in violations, "Luhn-invalid 16-digit number correctly evades"


# ── Attack #20: SECRET label as exfiltration kill-switch ─────────────────────

class TestSecretLabelKillSwitch:
    """
    Attack #20 — SECRET-labeled data must never reach the customer regardless
    of content, and must short-circuit all subsequent checks.
    """

    def test_secret_with_clean_text_blocked(self):
        result, mock_log = _run("The claim is approved.", _SECRET)
        assert not result.ok
        assert result.output == REFUSAL_MESSAGE
        mock_log.assert_called_once()
        assert mock_log.call_args.kwargs["action"] == "egress_blocked_secret"

    def test_secret_short_circuits_url_and_pii_checks(self):
        """SECRET kills before URL stripping or PII detection run."""
        text = "https://evil.com/x and SSN 123-45-6789"
        _, mock_log = _run(text, _SECRET)
        # Must be exactly ONE log entry (secret), not three (url + pii + secret)
        mock_log.assert_called_once()
        assert mock_log.call_args.kwargs["action"] == "egress_blocked_secret"

    def test_confidential_not_blocked_by_label(self):
        """CONFIDENTIAL label alone does not trigger the kill switch."""
        result, _ = _run("Your claim status: PENDING.", _CONFIDENTIAL)
        assert result.ok

    def test_secret_violation_in_violations_list(self):
        result, _ = _run("data", _SECRET)
        assert "secret_label" in result.violations
