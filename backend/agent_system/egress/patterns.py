"""PII detection patterns for the egress output filter (P10 — task 1.2.5).

Compiled once at import time.  All public API is pure — no I/O.
"""
from __future__ import annotations

import re

# SSN — requires separators to avoid colliding with 9-digit IDs
_SSN_RE = re.compile(r"\b\d{3}[-\s]\d{2}[-\s]\d{4}\b")

# US phone — last separator is required to cap false positives
_PHONE_RE = re.compile(
    r"\b(?:\+?1[\s.\-]?)?"     # optional country code
    r"\(?\d{3}\)?"             # area code with optional parens
    r"[\s.\-]?\d{3}"           # exchange
    r"[\s.\-]\d{4}\b"          # last 4 (separator required)
)

# Credit card — 4×4 digits with optional space/dash separators; Luhn-validated below
_CARD_CANDIDATE_RE = re.compile(r"\b(?:\d{4}[\s\-]?){3}\d{4}\b")


def _luhn_check(raw: str) -> bool:
    digits = [int(c) for c in raw if c.isdigit()]
    if not (13 <= len(digits) <= 19):
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def find_pii(text: str) -> list[str]:
    """Return list of PII violation type names found in *text*.

    Returns a list so the caller knows *which* patterns fired (useful for
    audit details and tests).  Stops at first credit-card hit to avoid noise.
    """
    violations: list[str] = []
    if _SSN_RE.search(text):
        violations.append("ssn")
    if _PHONE_RE.search(text):
        violations.append("phone")
    for m in _CARD_CANDIDATE_RE.finditer(text):
        if _luhn_check(m.group()):
            violations.append("credit_card")
            break
    return violations
