"""PDF sandbox client — P5 sandboxed file processing (task 1.3.1).

Public API:  parse_pdf(pdf_bytes: bytes) -> PDFParseResult

The function spawns a per-job Docker container (`secureclaim-pdf-sandbox`)
with --network=none, read-only rootfs, and full capability drop.  The raw
PDF bytes are written to the container's stdin; a single JSON object is read
from stdout and converted into a typed PDFParseResult.

Why per-job containers instead of a persistent service?
  A long-running parser service cannot use --network=none if it needs to
  be reached via HTTP.  Spawning per-job is the only way to combine literal
  network isolation with an HTTP-accessible host API (which runs outside
  Docker via `uv run uvicorn`).  The spawn overhead (~300 ms cold) is
  acceptable for file ingestion; the alternative (a UNIX-socket bridge)
  adds complexity without meaningful throughput benefit at our claim volume.

All extracted text is labeled UNTRUSTED regardless of PDF content — it is
external input that has not yet passed through the dual-LLM filter (P1).
The chars array is 1.3.4-ready: every character carries the coordinate and
styling metadata needed for white-on-white / micro-font / off-page detection.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Literal

from agent_system.ifc.labels import DataLabel, Label, Labeled
from agent_system.sanitisation.text import sanitise

MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MiB — reject before paying spawn cost
_PDF_MAGIC = b"%PDF-"
SANDBOX_IMAGE = "secureclaim-pdf-sandbox:latest"
SANDBOX_TIMEOUT_S = 30

# Security flags applied to every container spawn.  These implement P5:
#   --network=none          no outbound exfiltration from adversarial PDF content
#   --read-only             rootfs immutable (container writes only to tmpfs)
#   --tmpfs /tmp:…          ephemeral scratch space, non-executable, no setuid
#   --cap-drop=ALL          no Linux capabilities
#   --security-opt …        DAC_OVERRIDE and setuid bits cannot grant new caps
#   --memory / --pids-limit resource DoS protection (pathological PDFs)
#   --user=65534:65534      nobody:nogroup — unprivileged even inside container
#   --rm -i                 auto-remove after exit; -i keeps stdin open
_DOCKER_FLAGS: list[str] = [
    "--network=none",
    "--read-only",
    "--tmpfs", "/tmp:size=64m,noexec,nosuid,nodev",
    "--cap-drop=ALL",
    "--security-opt=no-new-privileges:true",
    "--memory=256m",
    "--pids-limit=64",
    "--user=65534:65534",
    "--rm",
    "-i",
]


@dataclass(frozen=True)
class CharData:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page_width: float
    page_height: float
    font_size: float
    font_name: str
    non_stroking_color: list | None


@dataclass(frozen=True)
class PageData:
    page_number: int
    text: str
    chars: tuple[CharData, ...]


@dataclass(frozen=True)
class PDFParseResult:
    """Result of parse_pdf().

    status == "CLEAN"    → labeled_text is set; all pages extracted.
    status == "REJECTED" → reject_reason explains why; labeled_text is None.
    status == "ERROR"    → sandbox crashed or timed out; labeled_text is None.
    """

    status: Literal["CLEAN", "REJECTED", "ERROR"]
    page_count: int
    pages: tuple[PageData, ...]
    findings: tuple[str, ...]
    reject_reason: str | None
    labeled_text: Labeled[str] | None


def _parse_char(raw: dict) -> CharData:
    return CharData(
        text=str(raw.get("text", "")),
        x0=float(raw.get("x0", 0.0)),
        y0=float(raw.get("y0", 0.0)),
        x1=float(raw.get("x1", 0.0)),
        y1=float(raw.get("y1", 0.0)),
        page_width=float(raw.get("page_width", 0.0)),
        page_height=float(raw.get("page_height", 0.0)),
        font_size=float(raw.get("font_size", 0.0)),
        font_name=str(raw.get("font_name", "")),
        non_stroking_color=raw.get("non_stroking_color"),
    )


def _build_result(raw: dict) -> PDFParseResult:
    """Convert the container's JSON output dict into a PDFParseResult."""
    status = raw.get("status", "ERROR")
    reject_reason = raw.get("reject_reason")
    findings = tuple(raw.get("findings", []))

    if status != "CLEAN":
        return PDFParseResult(
            status=status,  # type: ignore[arg-type]
            page_count=0,
            pages=(),
            findings=findings,
            reject_reason=reject_reason,
            labeled_text=None,
        )

    pages: list[PageData] = []
    for p in raw.get("pages", []):
        chars = tuple(_parse_char(c) for c in p.get("chars", []))
        pages.append(
            PageData(
                page_number=int(p.get("page_number", 0)),
                text=str(p.get("text", "")),
                chars=chars,
            )
        )

    # Concatenate all page text and run through the standard text sanitiser so
    # the labeled_text carries the same UNTRUSTED flag as any other external
    # input entering the pipeline.
    combined_text = "\n\n".join(p.text for p in pages)
    sanitise_result = sanitise(combined_text)

    return PDFParseResult(
        status="CLEAN",
        page_count=int(raw.get("page_count", len(pages))),
        pages=tuple(pages),
        findings=findings,
        reject_reason=None,
        labeled_text=sanitise_result.labeled,
    )


def parse_pdf(pdf_bytes: bytes) -> PDFParseResult:
    """Sandbox-parse *pdf_bytes* and return a typed PDFParseResult.

    Raises nothing — all error conditions are encoded in the returned
    PDFParseResult.status field ("REJECTED" or "ERROR").
    """
    # Pre-flight guards — fast path before paying the container spawn cost.
    if len(pdf_bytes) > MAX_PDF_BYTES:
        return PDFParseResult(
            status="REJECTED",
            page_count=0,
            pages=(),
            findings=(),
            reject_reason=f"file_too_large:{len(pdf_bytes)}",
            labeled_text=None,
        )

    if not pdf_bytes.startswith(_PDF_MAGIC):
        return PDFParseResult(
            status="REJECTED",
            page_count=0,
            pages=(),
            findings=(),
            reject_reason="invalid_magic_bytes",
            labeled_text=None,
        )

    cmd = ["docker", "run"] + _DOCKER_FLAGS + [SANDBOX_IMAGE]
    try:
        result = subprocess.run(
            cmd,
            input=pdf_bytes,
            capture_output=True,
            timeout=SANDBOX_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return PDFParseResult(
            status="ERROR",
            page_count=0,
            pages=(),
            findings=(),
            reject_reason="sandbox_timeout",
            labeled_text=None,
        )
    except FileNotFoundError:
        return PDFParseResult(
            status="ERROR",
            page_count=0,
            pages=(),
            findings=(),
            reject_reason="docker_not_found",
            labeled_text=None,
        )
    except Exception as exc:
        return PDFParseResult(
            status="ERROR",
            page_count=0,
            pages=(),
            findings=(),
            reject_reason=f"spawn_error:{exc}",
            labeled_text=None,
        )

    if not result.stdout:
        return PDFParseResult(
            status="ERROR",
            page_count=0,
            pages=(),
            findings=(),
            reject_reason="empty_sandbox_output",
            labeled_text=None,
        )

    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return PDFParseResult(
            status="ERROR",
            page_count=0,
            pages=(),
            findings=(),
            reject_reason=f"json_decode_error:{exc}",
            labeled_text=None,
        )

    return _build_result(raw)
