"""Image sandbox client — P5 sandboxed file processing (task 1.3.2).

Public API:  sanitise_image(image_bytes: bytes) -> ImageSanitiseResult

Spawns a per-job Docker container with the same security flags as the PDF
sandbox: --network=none, read-only rootfs, dropped capabilities, unprivileged
user.  Raw image bytes go in via stdin; a JSON object with metadata-stripped
re-encoded image bytes (base64) comes out via stdout.

Processing performed inside the sandbox (§2.5.2 steps 1+3):
  1. EXIF/XMP/IPTC metadata stripped; image re-encoded.
  3. LSB chi-square steganography heuristic (detection signal only — never
     blocks; steg_flag=True surfaces in the audit log for human review).

Vision pre-redaction (§2.5.2 step 2 — OCR + pixel-blur) is task 1.3.3.

Supported input formats: JPEG, PNG, GIF, WEBP.
All other formats are rejected by the client-side magic-byte check before
the container is ever spawned.

All derived text (metadata description) is labeled PUBLIC+UNTRUSTED.
"""
from __future__ import annotations

import base64
import json
import subprocess
from dataclasses import dataclass
from typing import Literal

from agent_system.ifc.labels import DataLabel, Label, Labeled

MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MiB
SANDBOX_IMAGE = "secureclaim-image-sandbox:latest"
SANDBOX_TIMEOUT_S = 30

_DOCKER_FLAGS: list[str] = [
    "--network=none",
    "--read-only",
    "--tmpfs", "/tmp:size=128m,noexec,nosuid,nodev",
    "--cap-drop=ALL",
    "--security-opt=no-new-privileges:true",
    "--memory=512m",
    "--pids-limit=64",
    "--user=65534:65534",
    "--rm",
    "-i",
]

# Maps (magic_prefix, optional_secondary_check_offset, secondary_bytes) → format name.
# WEBP requires RIFF header (bytes 0-3) AND "WEBP" at bytes 8-11.
# We validate in _detect_format() below rather than a flat dict.
_SUPPORTED_LABEL = frozenset({"JPEG", "PNG", "GIF", "WEBP"})


def _detect_format(data: bytes) -> str | None:
    """Return the image format name or None if unsupported/unrecognised."""
    if len(data) < 12:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "JPEG"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "PNG"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "GIF"
    # WEBP: RIFF....WEBP  (bytes 0-3 and 8-11)
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    return None


@dataclass(frozen=True)
class ImageSanitiseResult:
    """Result of sanitise_image().

    status == "CLEAN"    → re_encoded_bytes is set; metadata has been stripped.
    status == "REJECTED" → reject_reason explains why; re_encoded_bytes is None.
    status == "ERROR"    → sandbox crash or timeout; re_encoded_bytes is None.

    steg_flag=True is a detection signal for the audit log; it never blocks.
    """

    status: Literal["CLEAN", "REJECTED", "ERROR"]
    format: str | None           # original image format (JPEG, PNG, GIF, WEBP)
    re_encoded_format: str | None  # format of re_encoded_bytes ("JPEG" or "PNG")
    width: int | None
    height: int | None
    mode: str | None             # Pillow mode: RGB, RGBA, L, ...
    steg_flag: bool              # LSB chi-square flagged (detection signal only)
    steg_score: float | None     # chi2_stat/dof; None if test not run
    re_encoded_bytes: bytes | None   # metadata-stripped image bytes
    findings: tuple[str, ...]
    reject_reason: str | None
    labeled_metadata: Labeled[str] | None  # text summary for audit, UNTRUSTED


def _untrusted_label() -> Label:
    return Label(level=DataLabel.PUBLIC, untrusted=True)


def _build_result(raw: dict) -> ImageSanitiseResult:
    """Convert container JSON output into a typed ImageSanitiseResult."""
    status = raw.get("status", "ERROR")
    reject_reason = raw.get("reject_reason")
    findings = tuple(raw.get("findings", []))
    fmt = raw.get("format")
    re_fmt = raw.get("re_encoded_format")
    width = raw.get("width")
    height = raw.get("height")
    mode = raw.get("mode")
    steg_flag = bool(raw.get("steg_flag", False))
    steg_score_raw = raw.get("steg_score")
    steg_score = float(steg_score_raw) if steg_score_raw is not None else None

    if status != "CLEAN":
        return ImageSanitiseResult(
            status=status,  # type: ignore[arg-type]
            format=fmt,
            re_encoded_format=None,
            width=width,
            height=height,
            mode=mode,
            steg_flag=steg_flag,
            steg_score=steg_score,
            re_encoded_bytes=None,
            findings=findings,
            reject_reason=reject_reason,
            labeled_metadata=None,
        )

    re_encoded_b64 = raw.get("re_encoded_b64") or ""
    re_encoded_bytes = base64.b64decode(re_encoded_b64) if re_encoded_b64 else None

    metadata_text = (
        f"format={fmt} re_encoded_as={re_fmt} "
        f"size={width}x{height} mode={mode} "
        f"steg_flag={steg_flag} steg_score={steg_score}"
    )
    labeled_metadata = Labeled(
        value=f"<untrusted>{metadata_text}</untrusted>",
        label=_untrusted_label(),
    )

    return ImageSanitiseResult(
        status="CLEAN",
        format=fmt,
        re_encoded_format=re_fmt,
        width=int(width) if width is not None else None,
        height=int(height) if height is not None else None,
        mode=mode,
        steg_flag=steg_flag,
        steg_score=steg_score,
        re_encoded_bytes=re_encoded_bytes,
        findings=findings,
        reject_reason=None,
        labeled_metadata=labeled_metadata,
    )


def sanitise_image(image_bytes: bytes) -> ImageSanitiseResult:
    """Sandbox-sanitise *image_bytes* and return a typed ImageSanitiseResult.

    Raises nothing — all error conditions are encoded in the returned status.
    """
    # --- Pre-flight guards (no container spawn) ---
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return ImageSanitiseResult(
            status="REJECTED",
            format=None, re_encoded_format=None,
            width=None, height=None, mode=None,
            steg_flag=False, steg_score=None,
            re_encoded_bytes=None, findings=(),
            reject_reason=f"file_too_large:{len(image_bytes)}",
            labeled_metadata=None,
        )

    detected_format = _detect_format(image_bytes)
    if detected_format is None:
        return ImageSanitiseResult(
            status="REJECTED",
            format=None, re_encoded_format=None,
            width=None, height=None, mode=None,
            steg_flag=False, steg_score=None,
            re_encoded_bytes=None, findings=(),
            reject_reason="unsupported_format",
            labeled_metadata=None,
        )

    # --- Spawn sandbox ---
    cmd = ["docker", "run"] + _DOCKER_FLAGS + [SANDBOX_IMAGE]
    try:
        result = subprocess.run(
            cmd,
            input=image_bytes,
            capture_output=True,
            timeout=SANDBOX_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return ImageSanitiseResult(
            status="ERROR",
            format=detected_format, re_encoded_format=None,
            width=None, height=None, mode=None,
            steg_flag=False, steg_score=None,
            re_encoded_bytes=None, findings=(),
            reject_reason="sandbox_timeout",
            labeled_metadata=None,
        )
    except FileNotFoundError:
        return ImageSanitiseResult(
            status="ERROR",
            format=detected_format, re_encoded_format=None,
            width=None, height=None, mode=None,
            steg_flag=False, steg_score=None,
            re_encoded_bytes=None, findings=(),
            reject_reason="docker_not_found",
            labeled_metadata=None,
        )
    except Exception as exc:
        return ImageSanitiseResult(
            status="ERROR",
            format=detected_format, re_encoded_format=None,
            width=None, height=None, mode=None,
            steg_flag=False, steg_score=None,
            re_encoded_bytes=None, findings=(),
            reject_reason=f"spawn_error:{exc}",
            labeled_metadata=None,
        )

    if not result.stdout:
        return ImageSanitiseResult(
            status="ERROR",
            format=detected_format, re_encoded_format=None,
            width=None, height=None, mode=None,
            steg_flag=False, steg_score=None,
            re_encoded_bytes=None, findings=(),
            reject_reason="empty_sandbox_output",
            labeled_metadata=None,
        )

    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return ImageSanitiseResult(
            status="ERROR",
            format=detected_format, re_encoded_format=None,
            width=None, height=None, mode=None,
            steg_flag=False, steg_score=None,
            re_encoded_bytes=None, findings=(),
            reject_reason=f"json_decode_error:{exc}",
            labeled_metadata=None,
        )

    return _build_result(raw)
