"""Unit tests for the PDF sandbox client (task 1.3.1).

subprocess.run is mocked throughout — these tests exercise the client-side
logic in agent_system/sanitisation/pdf.py without requiring Docker.
"""
from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from agent_system.ifc.labels import DataLabel

pytestmark = pytest.mark.unit
from agent_system.sanitisation.pdf import (
    MAX_PDF_BYTES,
    CharData,
    PDFParseResult,
    _build_result,
    parse_pdf,
)

_PDF_MAGIC = b"%PDF-"
_MINIMAL_PDF = _PDF_MAGIC + b"-1.4 fake content"


def _make_completed_process(stdout: bytes, returncode: int = 0) -> MagicMock:
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.stdout = stdout
    proc.stderr = b""
    proc.returncode = returncode
    return proc


def _clean_json(pages: list | None = None) -> bytes:
    pages = pages or [
        {
            "page_number": 1,
            "text": "Hello world",
            "chars": [
                {
                    "text": "H",
                    "x0": 72.0,
                    "y0": 720.0,
                    "x1": 78.0,
                    "y1": 732.0,
                    "page_width": 612.0,
                    "page_height": 792.0,
                    "font_size": 12.0,
                    "font_name": "Helvetica",
                    "non_stroking_color": [0, 0, 0],
                }
            ],
        }
    ]
    return json.dumps(
        {
            "status": "CLEAN",
            "reject_reason": None,
            "page_count": len(pages),
            "pages": pages,
            "findings": [],
        }
    ).encode()


# ---------------------------------------------------------------------------
# Pre-flight guards (no Docker spawn)
# ---------------------------------------------------------------------------


class TestPreFlightGuards:
    def test_rejects_oversized_file(self):
        big = _PDF_MAGIC + b"x" * MAX_PDF_BYTES
        result = parse_pdf(big)
        assert result.status == "REJECTED"
        assert result.reject_reason.startswith("file_too_large:")

    def test_rejects_wrong_magic_bytes(self):
        result = parse_pdf(b"PK\x03\x04zip content")
        assert result.status == "REJECTED"
        assert result.reject_reason == "invalid_magic_bytes"

    def test_rejects_empty_bytes(self):
        result = parse_pdf(b"")
        assert result.status == "REJECTED"
        assert result.reject_reason == "invalid_magic_bytes"

    def test_exact_size_limit_passes_preflight(self):
        # MAX_PDF_BYTES exactly is allowed through (> is the check, not >=)
        exact = _PDF_MAGIC + b"x" * (MAX_PDF_BYTES - len(_PDF_MAGIC))
        # We don't care what Docker returns — just that preflight passes.
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(b"")
            result = parse_pdf(exact)
        # Empty stdout → ERROR, not REJECTED from preflight
        assert result.status == "ERROR"
        assert result.reject_reason == "empty_sandbox_output"


# ---------------------------------------------------------------------------
# Subprocess failure modes
# ---------------------------------------------------------------------------


class TestSubprocessFailures:
    def test_timeout_returns_error(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=30)
            result = parse_pdf(_MINIMAL_PDF)
        assert result.status == "ERROR"
        assert result.reject_reason == "sandbox_timeout"

    def test_docker_not_found_returns_error(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("docker not found")
            result = parse_pdf(_MINIMAL_PDF)
        assert result.status == "ERROR"
        assert result.reject_reason == "docker_not_found"

    def test_unexpected_exception_returns_error(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("permission denied")
            result = parse_pdf(_MINIMAL_PDF)
        assert result.status == "ERROR"
        assert result.reject_reason.startswith("spawn_error:")

    def test_empty_stdout_returns_error(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(b"")
            result = parse_pdf(_MINIMAL_PDF)
        assert result.status == "ERROR"
        assert result.reject_reason == "empty_sandbox_output"

    def test_invalid_json_stdout_returns_error(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(b"not json {{{")
            result = parse_pdf(_MINIMAL_PDF)
        assert result.status == "ERROR"
        assert result.reject_reason.startswith("json_decode_error:")


# ---------------------------------------------------------------------------
# Clean parse path
# ---------------------------------------------------------------------------


class TestCleanParse:
    def test_clean_result_has_labeled_text(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_clean_json())
            result = parse_pdf(_MINIMAL_PDF)
        assert result.status == "CLEAN"
        assert result.labeled_text is not None

    def test_labeled_text_is_public_untrusted(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_clean_json())
            result = parse_pdf(_MINIMAL_PDF)
        assert result.labeled_text.label.level == DataLabel.PUBLIC
        assert result.labeled_text.label.untrusted is True

    def test_labeled_text_is_wrapped(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_clean_json())
            result = parse_pdf(_MINIMAL_PDF)
        assert result.labeled_text.value.startswith("<untrusted>")
        assert result.labeled_text.value.endswith("</untrusted>")

    def test_page_count_matches(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_clean_json())
            result = parse_pdf(_MINIMAL_PDF)
        assert result.page_count == 1
        assert len(result.pages) == 1

    def test_page_text_extracted(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_clean_json())
            result = parse_pdf(_MINIMAL_PDF)
        assert result.pages[0].text == "Hello world"

    def test_char_data_parsed(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_clean_json())
            result = parse_pdf(_MINIMAL_PDF)
        char = result.pages[0].chars[0]
        assert isinstance(char, CharData)
        assert char.text == "H"
        assert char.font_name == "Helvetica"
        assert char.font_size == 12.0
        assert char.non_stroking_color == [0, 0, 0]

    def test_char_coordinates_preserved(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_clean_json())
            result = parse_pdf(_MINIMAL_PDF)
        char = result.pages[0].chars[0]
        assert char.x0 == 72.0
        assert char.y0 == 720.0
        assert char.page_width == 612.0
        assert char.page_height == 792.0

    def test_null_non_stroking_color_allowed(self):
        pages = [
            {
                "page_number": 1,
                "text": "test",
                "chars": [
                    {
                        "text": "t",
                        "x0": 0.0, "y0": 0.0, "x1": 6.0, "y1": 12.0,
                        "page_width": 612.0, "page_height": 792.0,
                        "font_size": 10.0, "font_name": "Times",
                        "non_stroking_color": None,
                    }
                ],
            }
        ]
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_clean_json(pages))
            result = parse_pdf(_MINIMAL_PDF)
        assert result.pages[0].chars[0].non_stroking_color is None

    def test_multipage_pdf(self):
        pages = [
            {
                "page_number": i,
                "text": f"Page {i} text",
                "chars": [],
            }
            for i in range(1, 4)
        ]
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_clean_json(pages))
            result = parse_pdf(_MINIMAL_PDF)
        assert result.page_count == 3
        assert len(result.pages) == 3
        assert result.pages[2].text == "Page 3 text"

    def test_combined_text_in_labeled_value(self):
        pages = [
            {"page_number": 1, "text": "First page", "chars": []},
            {"page_number": 2, "text": "Second page", "chars": []},
        ]
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_clean_json(pages))
            result = parse_pdf(_MINIMAL_PDF)
        assert "First page" in result.labeled_text.value
        assert "Second page" in result.labeled_text.value


# ---------------------------------------------------------------------------
# Rejected / structural threat paths
# ---------------------------------------------------------------------------


class TestRejectedPaths:
    def _rejected_json(self, reason: str) -> bytes:
        return json.dumps(
            {
                "status": "REJECTED",
                "reject_reason": reason,
                "page_count": 0,
                "pages": [],
                "findings": [],
            }
        ).encode()

    def test_javascript_rejection(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(
                self._rejected_json("javascript")
            )
            result = parse_pdf(_MINIMAL_PDF)
        assert result.status == "REJECTED"
        assert result.reject_reason == "javascript"
        assert result.labeled_text is None

    def test_embedded_file_rejection(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(
                self._rejected_json("embedded_file")
            )
            result = parse_pdf(_MINIMAL_PDF)
        assert result.status == "REJECTED"
        assert result.reject_reason == "embedded_file"

    def test_xfa_form_rejection(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(
                self._rejected_json("xfa_form")
            )
            result = parse_pdf(_MINIMAL_PDF)
        assert result.status == "REJECTED"
        assert result.reject_reason == "xfa_form"

    def test_launch_action_rejection(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(
                self._rejected_json("launch_action")
            )
            result = parse_pdf(_MINIMAL_PDF)
        assert result.status == "REJECTED"
        assert result.reject_reason == "launch_action"

    def test_rejected_has_no_pages(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(
                self._rejected_json("javascript")
            )
            result = parse_pdf(_MINIMAL_PDF)
        assert result.pages == ()
        assert result.page_count == 0


# ---------------------------------------------------------------------------
# _build_result unit tests (direct, no subprocess)
# ---------------------------------------------------------------------------


class TestBuildResult:
    def test_clean_dict_produces_clean_result(self):
        raw = {
            "status": "CLEAN",
            "reject_reason": None,
            "page_count": 1,
            "pages": [{"page_number": 1, "text": "hello", "chars": []}],
            "findings": [],
        }
        result = _build_result(raw)
        assert result.status == "CLEAN"
        assert result.page_count == 1

    def test_rejected_dict_produces_rejected_result(self):
        raw = {
            "status": "REJECTED",
            "reject_reason": "javascript",
            "page_count": 0,
            "pages": [],
            "findings": [],
        }
        result = _build_result(raw)
        assert result.status == "REJECTED"
        assert result.labeled_text is None

    def test_findings_preserved(self):
        raw = {
            "status": "CLEAN",
            "reject_reason": None,
            "page_count": 1,
            "pages": [{"page_number": 1, "text": "x", "chars": []}],
            "findings": ["observation_a", "observation_b"],
        }
        result = _build_result(raw)
        assert "observation_a" in result.findings
        assert "observation_b" in result.findings

    def test_result_is_frozen(self):
        raw = {
            "status": "CLEAN",
            "reject_reason": None,
            "page_count": 1,
            "pages": [{"page_number": 1, "text": "immutable", "chars": []}],
            "findings": [],
        }
        result = _build_result(raw)
        with pytest.raises((AttributeError, TypeError)):
            result.status = "REJECTED"  # type: ignore[misc]

    def test_docker_run_command_includes_network_none(self):
        """Verify the subprocess command passed to Docker has --network=none."""
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_clean_json())
            parse_pdf(_MINIMAL_PDF)
        cmd = mock_run.call_args[0][0]
        assert "--network=none" in cmd

    def test_docker_run_command_includes_read_only(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_clean_json())
            parse_pdf(_MINIMAL_PDF)
        cmd = mock_run.call_args[0][0]
        assert "--read-only" in cmd

    def test_docker_run_command_drops_all_caps(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_clean_json())
            parse_pdf(_MINIMAL_PDF)
        cmd = mock_run.call_args[0][0]
        assert "--cap-drop=ALL" in cmd

    def test_pdf_bytes_sent_as_stdin(self):
        with patch("agent_system.sanitisation.pdf.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_clean_json())
            parse_pdf(_MINIMAL_PDF)
        kwargs = mock_run.call_args[1]
        assert kwargs["input"] == _MINIMAL_PDF
