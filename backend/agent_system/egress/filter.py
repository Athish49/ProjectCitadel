"""Egress output filter (P10 — task 1.2.5).

Every customer-visible string must pass through filter_output() before
delivery.  Four checks run in order:

  1. SECRET label       → block entirely, log for forensics.  Short-circuits.
  2. URL allowlist      → strip non-allowlisted URLs inline, audit each one.
  3. PII patterns       → block entirely if SSN / phone / credit card found.
  4. Length cap         → truncate at MAX_OUTPUT_CHARS.

Steps 2–4 stack; step 1 is exclusive.  The caller must commit conn after the
call returns (same contract as ToolRegistry).

ok=False means the original was blocked; output is always safe to deliver.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import psycopg

from audit.chain import append_log
from agent_system.ifc.labels import DataLabel, Label
from agent_system.egress.allowlist import strip_urls
from agent_system.egress.patterns import find_pii

REFUSAL_MESSAGE = "I'm not able to share that information. Please contact support."
MAX_OUTPUT_CHARS = 2000


@dataclass
class FilterResult:
    ok: bool
    output: str
    violations: list[str] = field(default_factory=list)
    log_ids: list[int] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.ok


def filter_output(
    conn: psycopg.Connection,
    *,
    text: str,
    source_label: Label,
    calling_agent_id: str,
    trace_id: uuid.UUID | None = None,
) -> FilterResult:
    """Run all egress checks and return a FilterResult.

    Never raises.  Caller must commit conn.
    """
    violations: list[str] = []
    log_ids: list[int] = []

    # ── Step 1: SECRET label — kill switch ───────────────────────────────────
    if source_label.level == DataLabel.SECRET:
        log_id = append_log(
            conn,
            agent_id=calling_agent_id,
            action="egress_blocked_secret",
            target="egress/output",
            data_label="CONFIDENTIAL",
            trace_id=trace_id,
            details={
                "source_label": str(source_label),
                "original_length": len(text),
            },
            security_event=True,
        )
        violations.append("secret_label")
        return FilterResult(
            ok=False,
            output=REFUSAL_MESSAGE,
            violations=violations,
            log_ids=[log_id],
        )

    working = text

    # ── Step 2: URL allowlist — strip inline ─────────────────────────────────
    working, stripped_urls = strip_urls(working)
    for bad_url in stripped_urls:
        log_id = append_log(
            conn,
            agent_id=calling_agent_id,
            action="egress_url_stripped",
            target="egress/output",
            data_label="CONFIDENTIAL",
            trace_id=trace_id,
            details={"url": bad_url},
            security_event=True,
        )
        log_ids.append(log_id)
        violations.append(f"url:{bad_url}")

    # ── Step 3: PII — block whole response ───────────────────────────────────
    pii_types = find_pii(working)
    if pii_types:
        log_id = append_log(
            conn,
            agent_id=calling_agent_id,
            action="egress_blocked_pii",
            target="egress/output",
            data_label="CONFIDENTIAL",
            trace_id=trace_id,
            details={"pii_types": pii_types},
            security_event=True,
        )
        log_ids.append(log_id)
        violations.extend(f"pii:{t}" for t in pii_types)
        return FilterResult(
            ok=False,
            output=REFUSAL_MESSAGE,
            violations=violations,
            log_ids=log_ids,
        )

    # ── Step 4: length cap ────────────────────────────────────────────────────
    if len(working) > MAX_OUTPUT_CHARS:
        working = working[:MAX_OUTPUT_CHARS]
        log_id = append_log(
            conn,
            agent_id=calling_agent_id,
            action="egress_truncated",
            target="egress/output",
            data_label="CONFIDENTIAL",
            trace_id=trace_id,
            details={"original_length": len(text), "cap": MAX_OUTPUT_CHARS},
            security_event=False,
        )
        log_ids.append(log_id)
        violations.append("truncated")

    return FilterResult(ok=True, output=working, violations=violations, log_ids=log_ids)
