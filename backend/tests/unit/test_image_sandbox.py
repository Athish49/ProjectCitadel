"""Unit tests for the image sandbox client (task 1.3.2).

subprocess.run is mocked throughout — no Docker required.
"""
from __future__ import annotations

import base64
import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from agent_system.ifc.labels import DataLabel
from agent_system.sanitisation.image import (
    MAX_IMAGE_BYTES,
    ImageSanitiseResult,
    _build_result,
    _detect_format,
    sanitise_image,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Minimal magic-byte stubs for each supported format
# ---------------------------------------------------------------------------
_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
_GIF = b"GIF89a" + b"\x00" * 20
_WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 20


def _make_proc(stdout: bytes, returncode: int = 0) -> MagicMock:
    p = MagicMock(spec=subprocess.CompletedProcess)
    p.stdout = stdout
    p.stderr = b""
    p.returncode = returncode
    return p


def _clean_json(
    fmt: str = "PNG",
    re_fmt: str = "PNG",
    w: int = 100,
    h: int = 100,
    mode: str = "RGB",
    steg_flag: bool = False,
    steg_score: float | None = 50.0,
    findings: list | None = None,
) -> bytes:
    dummy_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    return json.dumps(
        {
            "status": "CLEAN",
            "reject_reason": None,
            "format": fmt,
            "re_encoded_format": re_fmt,
            "width": w,
            "height": h,
            "mode": mode,
            "steg_flag": steg_flag,
            "steg_score": steg_score,
            "re_encoded_b64": base64.b64encode(dummy_png).decode(),
            "findings": findings or [],
        }
    ).encode()


def _rejected_json(reason: str) -> bytes:
    return json.dumps(
        {
            "status": "REJECTED",
            "reject_reason": reason,
            "format": None, "re_encoded_format": None,
            "width": None, "height": None, "mode": None,
            "steg_flag": False, "steg_score": None,
            "re_encoded_b64": None, "findings": [],
        }
    ).encode()


# ---------------------------------------------------------------------------
# _detect_format
# ---------------------------------------------------------------------------


class TestDetectFormat:
    def test_jpeg(self):
        assert _detect_format(_JPEG) == "JPEG"

    def test_png(self):
        assert _detect_format(_PNG) == "PNG"

    def test_gif87a(self):
        assert _detect_format(b"GIF87a" + b"\x00" * 20) == "GIF"

    def test_gif89a(self):
        assert _detect_format(_GIF) == "GIF"

    def test_webp_valid(self):
        assert _detect_format(_WEBP) == "WEBP"

    def test_webp_riff_only_not_matched(self):
        # RIFF header without WEBP identifier (e.g. WAV) must not match
        wav = b"RIFF\x00\x00\x00\x00WAVEfmt " + b"\x00" * 10
        assert _detect_format(wav) is None

    def test_pdf_not_matched(self):
        assert _detect_format(b"%PDF-1.4 content") is None

    def test_too_short_returns_none(self):
        assert _detect_format(b"\xff\xd8") is None

    def test_empty_returns_none(self):
        assert _detect_format(b"") is None

    def test_zip_not_matched(self):
        assert _detect_format(b"PK\x03\x04" + b"\x00" * 20) is None


# ---------------------------------------------------------------------------
# Pre-flight guards
# ---------------------------------------------------------------------------


class TestPreFlightGuards:
    def test_rejects_oversized_file(self):
        big = _JPEG + b"x" * MAX_IMAGE_BYTES
        result = sanitise_image(big)
        assert result.status == "REJECTED"
        assert result.reject_reason.startswith("file_too_large:")

    def test_rejects_unsupported_format(self):
        result = sanitise_image(b"%PDF-1.4 not an image")
        assert result.status == "REJECTED"
        assert result.reject_reason == "unsupported_format"

    def test_rejects_empty_bytes(self):
        result = sanitise_image(b"")
        assert result.status == "REJECTED"
        assert result.reject_reason == "unsupported_format"

    def test_exact_size_limit_passes_preflight(self):
        # exactly MAX_IMAGE_BYTES is allowed (> is the check, not >=)
        exact = _PNG + b"x" * (MAX_IMAGE_BYTES - len(_PNG))
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(b"")
            result = sanitise_image(exact)
        assert result.status == "ERROR"
        assert result.reject_reason == "empty_sandbox_output"


# ---------------------------------------------------------------------------
# Subprocess failure modes
# ---------------------------------------------------------------------------


class TestSubprocessFailures:
    def test_timeout(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=30)
            result = sanitise_image(_JPEG)
        assert result.status == "ERROR"
        assert result.reject_reason == "sandbox_timeout"

    def test_docker_not_found(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.side_effect = FileNotFoundError("no docker")
            result = sanitise_image(_PNG)
        assert result.status == "ERROR"
        assert result.reject_reason == "docker_not_found"

    def test_os_error(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.side_effect = OSError("broken pipe")
            result = sanitise_image(_GIF)
        assert result.status == "ERROR"
        assert result.reject_reason.startswith("spawn_error:")

    def test_empty_stdout(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(b"")
            result = sanitise_image(_WEBP)
        assert result.status == "ERROR"
        assert result.reject_reason == "empty_sandbox_output"

    def test_invalid_json(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(b"not-json{{{")
            result = sanitise_image(_PNG)
        assert result.status == "ERROR"
        assert result.reject_reason.startswith("json_decode_error:")


# ---------------------------------------------------------------------------
# Clean path
# ---------------------------------------------------------------------------


class TestCleanPath:
    def test_status_clean(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_clean_json())
            result = sanitise_image(_PNG)
        assert result.status == "CLEAN"

    def test_re_encoded_bytes_present(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_clean_json())
            result = sanitise_image(_PNG)
        assert result.re_encoded_bytes is not None
        assert len(result.re_encoded_bytes) > 0

    def test_labeled_metadata_is_public_untrusted(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_clean_json())
            result = sanitise_image(_PNG)
        assert result.labeled_metadata is not None
        assert result.labeled_metadata.label.level == DataLabel.PUBLIC
        assert result.labeled_metadata.label.untrusted is True

    def test_labeled_metadata_wrapped(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_clean_json())
            result = sanitise_image(_PNG)
        assert result.labeled_metadata.value.startswith("<untrusted>")
        assert result.labeled_metadata.value.endswith("</untrusted>")

    def test_dimensions_parsed(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_clean_json(w=640, h=480))
            result = sanitise_image(_JPEG)
        assert result.width == 640
        assert result.height == 480

    def test_mode_parsed(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_clean_json(mode="RGBA"))
            result = sanitise_image(_PNG)
        assert result.mode == "RGBA"

    def test_format_fields_parsed(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_clean_json(fmt="JPEG", re_fmt="JPEG"))
            result = sanitise_image(_JPEG)
        assert result.format == "JPEG"
        assert result.re_encoded_format == "JPEG"

    def test_findings_is_tuple(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_clean_json())
            result = sanitise_image(_PNG)
        assert isinstance(result.findings, tuple)

    def test_reject_reason_none_for_clean(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_clean_json())
            result = sanitise_image(_PNG)
        assert result.reject_reason is None

    def test_result_is_frozen(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_clean_json())
            result = sanitise_image(_PNG)
        with pytest.raises((AttributeError, TypeError)):
            result.status = "ERROR"  # type: ignore[misc]

    def test_multiframe_finding_preserved(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(
                _clean_json(findings=["multi_frame_truncated:frame_0_of_12"])
            )
            result = sanitise_image(_GIF)
        assert any("multi_frame_truncated" in f for f in result.findings)


# ---------------------------------------------------------------------------
# Steganography heuristic
# ---------------------------------------------------------------------------


class TestStegHeuristic:
    def test_steg_flag_false_not_suspicious(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_clean_json(steg_flag=False, steg_score=42.5))
            result = sanitise_image(_PNG)
        assert result.steg_flag is False
        assert result.steg_score == pytest.approx(42.5)

    def test_steg_flag_true_flagged(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(
                _clean_json(
                    steg_flag=True,
                    steg_score=0.2,
                    findings=["lsb_steg_suspected"],
                )
            )
            result = sanitise_image(_PNG)
        assert result.steg_flag is True
        assert result.steg_score == pytest.approx(0.2)
        assert "lsb_steg_suspected" in result.findings

    def test_steg_score_none_for_jpeg(self):
        # JPEG input → steg test skipped → score is null
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(
                _clean_json(fmt="JPEG", steg_flag=False, steg_score=None)
            )
            result = sanitise_image(_JPEG)
        assert result.steg_score is None

    def test_steg_flag_true_does_not_change_status(self):
        # Steg heuristic is a signal only — must not change status to REJECTED
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(
                _clean_json(steg_flag=True, steg_score=0.05)
            )
            result = sanitise_image(_PNG)
        assert result.status == "CLEAN"


# ---------------------------------------------------------------------------
# Rejected paths
# ---------------------------------------------------------------------------


class TestRejectedPaths:
    def test_unrecognised_format_rejection(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_rejected_json("unrecognised_image_format"))
            result = sanitise_image(_PNG)
        assert result.status == "REJECTED"
        assert result.re_encoded_bytes is None
        assert result.labeled_metadata is None

    def test_pixel_bomb_rejection(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_rejected_json("pixel_bomb:2000000000"))
            result = sanitise_image(_PNG)
        assert result.status == "REJECTED"
        assert result.reject_reason.startswith("pixel_bomb")

    def test_dimension_exceeded_rejection(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(
                _rejected_json("image_dimension_exceeded:20000x20000")
            )
            result = sanitise_image(_JPEG)
        assert result.status == "REJECTED"

    def test_rejected_has_no_re_encoded_bytes(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_rejected_json("unrecognised_image_format"))
            result = sanitise_image(_PNG)
        assert result.re_encoded_bytes is None


# ---------------------------------------------------------------------------
# Docker command construction
# ---------------------------------------------------------------------------


class TestDockerCommand:
    def test_network_none_in_cmd(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_clean_json())
            sanitise_image(_PNG)
        cmd = m.call_args[0][0]
        assert "--network=none" in cmd

    def test_read_only_in_cmd(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_clean_json())
            sanitise_image(_PNG)
        cmd = m.call_args[0][0]
        assert "--read-only" in cmd

    def test_cap_drop_all_in_cmd(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_clean_json())
            sanitise_image(_PNG)
        cmd = m.call_args[0][0]
        assert "--cap-drop=ALL" in cmd

    def test_image_bytes_sent_as_stdin(self):
        with patch("agent_system.sanitisation.image.subprocess.run") as m:
            m.return_value = _make_proc(_clean_json())
            sanitise_image(_JPEG)
        kwargs = m.call_args[1]
        assert kwargs["input"] == _JPEG


# ---------------------------------------------------------------------------
# _build_result direct tests
# ---------------------------------------------------------------------------


class TestBuildResult:
    def _clean_raw(self, **overrides) -> dict:
        dummy = b"\x89PNG" + b"\x00" * 32
        base = {
            "status": "CLEAN",
            "reject_reason": None,
            "format": "PNG",
            "re_encoded_format": "PNG",
            "width": 10,
            "height": 10,
            "mode": "RGB",
            "steg_flag": False,
            "steg_score": 25.0,
            "re_encoded_b64": base64.b64encode(dummy).decode(),
            "findings": [],
        }
        base.update(overrides)
        return base

    def test_clean_status(self):
        result = _build_result(self._clean_raw())
        assert result.status == "CLEAN"

    def test_rejected_produces_no_re_encoded(self):
        raw = {
            "status": "REJECTED", "reject_reason": "test",
            "format": "PNG", "re_encoded_format": None,
            "width": None, "height": None, "mode": None,
            "steg_flag": False, "steg_score": None,
            "re_encoded_b64": None, "findings": [],
        }
        result = _build_result(raw)
        assert result.status == "REJECTED"
        assert result.re_encoded_bytes is None
        assert result.labeled_metadata is None

    def test_metadata_text_contains_dimensions(self):
        result = _build_result(self._clean_raw(width=320, height=240))
        assert "320" in result.labeled_metadata.value
        assert "240" in result.labeled_metadata.value

    def test_steg_score_float_conversion(self):
        result = _build_result(self._clean_raw(steg_score=3.14))
        assert isinstance(result.steg_score, float)
        assert result.steg_score == pytest.approx(3.14)
