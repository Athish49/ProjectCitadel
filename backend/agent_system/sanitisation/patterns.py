"""Injection pattern detection for the text sanitiser (task 1.2.6).

Patterns are detection signals, not a primary defence — the dual-LLM
architecture (P1) is.  Every pattern that fires is recorded in
SanitiseResult.detections for the caller to audit.

All regexes are compiled once at import time.
"""
from __future__ import annotations

import re

# Each entry is (name, compiled_pattern).  Names appear verbatim in
# SanitiseResult.detections and in audit log details — keep them stable.
INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Instruction override
    (
        "ignore_instructions",
        re.compile(
            r"ignore\s+(?:previous|all|above)\s+instructions", re.IGNORECASE
        ),
    ),
    (
        "forget_instructions",
        re.compile(
            r"forget\s+(?:your\s+)?(?:previous\s+)?instructions", re.IGNORECASE
        ),
    ),
    (
        "disregard_instructions",
        re.compile(
            r"disregard\s+(?:all\s+)?(?:previous\s+)?instructions", re.IGNORECASE
        ),
    ),
    (
        "override_instructions",
        re.compile(r"override\s+(?:previous\s+)?instructions", re.IGNORECASE),
    ),
    (
        "new_instructions",
        re.compile(r"new\s+instructions\s*:", re.IGNORECASE),
    ),
    # Role hijack
    (
        "act_as",
        re.compile(r"\bact\s+as\b", re.IGNORECASE),
    ),
    (
        "you_are_now",
        re.compile(r"\byou\s+(?:are|will\s+be)\s+now\b", re.IGNORECASE),
    ),
    # System-prompt prefix mimicry
    (
        "system_prefix",
        re.compile(
            r"(?:^|\n)\s*\[?\s*system\s*\]?\s*:", re.IGNORECASE | re.MULTILINE
        ),
    ),
    # Generic jailbreak keywords
    (
        "jailbreak",
        re.compile(r"\bjailbreak\b", re.IGNORECASE),
    ),
    (
        "dan_mode",
        re.compile(r"\b(?:DAN|do\s+anything\s+now)\b", re.IGNORECASE),
    ),
    # LLM-specific escape tokens (ChatML, Llama, etc.)
    (
        "ml_token",
        re.compile(
            r"<\|(?:im_start|im_end|endoftext|system|user|assistant)\|>"
            r"|(?:^|(?<=\s))<s>(?:\s|$)",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    # HTML-style system/prompt tags
    (
        "system_tag",
        re.compile(
            r"<\s*(?:system|prompt|instruction|context)\s*/?>", re.IGNORECASE
        ),
    ),
]


def detect_patterns(text: str) -> list[str]:
    """Return names of all patterns that match *text*."""
    return [name for name, pat in INJECTION_PATTERNS if pat.search(text)]
