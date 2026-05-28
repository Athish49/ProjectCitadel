"""Integration tests for the PDF sandbox container (task 1.3.1).

Requires:
  - Docker daemon accessible on the host socket.
  - The image `secureclaim-pdf-sandbox:latest` already built
    (`make build-pdf-sandbox`).
  - pypdf installed in the dev environment (`uv sync --group dev`).

Run via:
  make test-pdf-sandbox

These tests exercise the real container — no mocks.  The most critical
assertion is `test_no_network_access`, which verifies the Phase 1 milestone:
"Sandboxes have no network access (verified)."
"""
from __future__ import annotations

import io
import json
import subprocess

import pytest

from agent_system.sanitisation.pdf import (
    SANDBOX_IMAGE,
    SANDBOX_TIMEOUT_S,
    _DOCKER_FLAGS,
    parse_pdf,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _docker_available() -> bool:
    try:
        r = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=5
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _image_exists() -> bool:
    try:
        r = subprocess.run(
            ["docker", "image", "inspect", SANDBOX_IMAGE],
            capture_output=True,
            timeout=5,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


requires_sandbox = pytest.mark.skipif(
    not (_docker_available() and _image_exists()),
    reason=f"Docker not available or image {SANDBOX_IMAGE} not built "
           "(run: make build-pdf-sandbox)",
)


def _make_blank_pdf(num_pages: int = 1) -> bytes:
    """Generate a minimal valid PDF with blank pages using pypdf."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_text_pdf(text: str) -> bytes:
    """Generate a PDF with a single page containing visible text."""
    from pypdf import PdfWriter
    from pypdf.generic import (
        ArrayObject,
        ContentStream,
        DecodedStreamObject,
        NameObject,
        NumberObject,
    )

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    # Embed Helvetica font reference and draw text via content stream.
    font_name = NameObject("/F1")
    font_dict = {
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    }
    from pypdf.generic import DictionaryObject
    font_obj = DictionaryObject(font_dict)
    font_ref = writer._add_object(font_obj)

    resources = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {font_name: font_ref}
            )
        }
    )
    page[NameObject("/Resources")] = resources

    stream_content = (
        f"BT\n/F1 12 Tf\n72 720 Td\n({text}) Tj\nET\n"
    ).encode()
    stream_obj = DecodedStreamObject()
    stream_obj.set_data(stream_content)
    stream_ref = writer._add_object(stream_obj)
    page[NameObject("/Contents")] = stream_ref

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Sandbox isolation
# ---------------------------------------------------------------------------


@requires_sandbox
class TestNetworkIsolation:
    def test_no_network_access(self):
        """Phase 1 milestone: sandbox containers must have no network access.

        We attempt a TCP connection to an external host from inside the
        container.  With --network=none the attempt must fail (non-zero exit
        or timeout).  A successful connection would be a critical security
        failure.
        """
        # Use a Python one-liner that exits 0 only if it can open a socket.
        probe_script = (
            "import socket, sys\n"
            "try:\n"
            "    s = socket.create_connection(('8.8.8.8', 53), timeout=3)\n"
            "    s.close()\n"
            "    sys.exit(0)\n"
            "except Exception:\n"
            "    sys.exit(1)\n"
        )
        cmd = (
            ["docker", "run"]
            + _DOCKER_FLAGS
            + [SANDBOX_IMAGE, "python3", "-c", probe_script]
        )
        # Override ENTRYPOINT so we can run our probe directly.
        cmd_with_override = (
            ["docker", "run", "--entrypoint=python3"]
            + _DOCKER_FLAGS
            + [SANDBOX_IMAGE, "-c", probe_script]
        )
        result = subprocess.run(
            cmd_with_override,
            capture_output=True,
            timeout=SANDBOX_TIMEOUT_S,
        )
        assert result.returncode != 0, (
            "CRITICAL: sandbox container successfully made a network connection. "
            "--network=none is not being applied."
        )

    def test_filesystem_is_read_only(self):
        """Container rootfs must be immutable (--read-only flag)."""
        probe_script = (
            "import sys\n"
            "try:\n"
            "    open('/rootfs_write_probe', 'w').close()\n"
            "    sys.exit(0)\n"
            "except OSError:\n"
            "    sys.exit(1)\n"
        )
        cmd = (
            ["docker", "run", "--entrypoint=python3"]
            + _DOCKER_FLAGS
            + [SANDBOX_IMAGE, "-c", probe_script]
        )
        result = subprocess.run(cmd, capture_output=True, timeout=SANDBOX_TIMEOUT_S)
        assert result.returncode != 0, (
            "Container rootfs is writable — --read-only is not being applied."
        )

    def test_tmp_is_writable(self):
        """The --tmpfs /tmp mount must be writable (scratch space for pdfplumber)."""
        probe_script = (
            "import sys, tempfile, os\n"
            "try:\n"
            "    with tempfile.NamedTemporaryFile(dir='/tmp', delete=False) as f:\n"
            "        f.write(b'ok')\n"
            "    sys.exit(0)\n"
            "except Exception as e:\n"
            "    print(e, file=sys.stderr)\n"
            "    sys.exit(1)\n"
        )
        cmd = (
            ["docker", "run", "--entrypoint=python3"]
            + _DOCKER_FLAGS
            + [SANDBOX_IMAGE, "-c", probe_script]
        )
        result = subprocess.run(cmd, capture_output=True, timeout=SANDBOX_TIMEOUT_S)
        assert result.returncode == 0, (
            f"/tmp is not writable inside sandbox: {result.stderr.decode()}"
        )

    def test_runs_as_unprivileged_user(self):
        """Container must run as uid=65534, not root."""
        probe_script = "import os; print(os.getuid())"
        cmd = (
            ["docker", "run", "--entrypoint=python3"]
            + _DOCKER_FLAGS
            + [SANDBOX_IMAGE, "-c", probe_script]
        )
        result = subprocess.run(cmd, capture_output=True, timeout=SANDBOX_TIMEOUT_S)
        uid = result.stdout.strip().decode()
        assert uid == "65534", f"Expected uid=65534, got {uid!r}"


# ---------------------------------------------------------------------------
# End-to-end parse through real container
# ---------------------------------------------------------------------------


@requires_sandbox
class TestEndToEndParse:
    def test_blank_pdf_parses_clean(self):
        pdf_bytes = _make_blank_pdf(1)
        result = parse_pdf(pdf_bytes)
        assert result.status == "CLEAN"
        assert result.page_count == 1

    def test_blank_pdf_labeled_untrusted(self):
        from agent_system.ifc.labels import DataLabel

        pdf_bytes = _make_blank_pdf(1)
        result = parse_pdf(pdf_bytes)
        assert result.labeled_text is not None
        assert result.labeled_text.label.untrusted is True
        assert result.labeled_text.label.level == DataLabel.PUBLIC

    def test_multipage_blank_pdf(self):
        pdf_bytes = _make_blank_pdf(3)
        result = parse_pdf(pdf_bytes)
        assert result.status == "CLEAN"
        assert result.page_count == 3
        assert len(result.pages) == 3

    def test_pages_are_immutable_tuples(self):
        pdf_bytes = _make_blank_pdf(1)
        result = parse_pdf(pdf_bytes)
        assert isinstance(result.pages, tuple)

    def test_labeled_text_wrapped_in_untrusted_tags(self):
        pdf_bytes = _make_blank_pdf(1)
        result = parse_pdf(pdf_bytes)
        assert result.labeled_text.value.startswith("<untrusted>")
        assert result.labeled_text.value.endswith("</untrusted>")

    def test_reject_reason_is_none_for_clean(self):
        pdf_bytes = _make_blank_pdf(1)
        result = parse_pdf(pdf_bytes)
        assert result.reject_reason is None

    def test_findings_is_tuple(self):
        pdf_bytes = _make_blank_pdf(1)
        result = parse_pdf(pdf_bytes)
        assert isinstance(result.findings, tuple)

    def test_container_exits_cleanly(self):
        """Verify the container process itself exits 0 for a clean PDF."""
        pdf_bytes = _make_blank_pdf(1)
        cmd = ["docker", "run"] + _DOCKER_FLAGS + [SANDBOX_IMAGE]
        result = subprocess.run(
            cmd, input=pdf_bytes, capture_output=True, timeout=SANDBOX_TIMEOUT_S
        )
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["status"] == "CLEAN"

    def test_empty_stdin_rejected_by_container(self):
        """Container must handle empty stdin gracefully."""
        cmd = ["docker", "run"] + _DOCKER_FLAGS + [SANDBOX_IMAGE]
        result = subprocess.run(
            cmd, input=b"", capture_output=True, timeout=SANDBOX_TIMEOUT_S
        )
        payload = json.loads(result.stdout)
        assert payload["status"] == "REJECTED"
        assert payload["reject_reason"] == "empty_input"

    def test_non_pdf_bytes_rejected_by_client(self):
        """Client-side magic-byte check must fire before Docker spawn."""
        result = parse_pdf(b"\x89PNG\r\n\x1a\n")
        assert result.status == "REJECTED"
        assert result.reject_reason == "invalid_magic_bytes"

    def test_oversized_file_rejected_by_client(self):
        """Client must reject files > MAX_PDF_BYTES without spawning Docker."""
        big = b"%PDF-1.4 " + b"x" * (10 * 1024 * 1024 + 1)
        result = parse_pdf(big)
        assert result.status == "REJECTED"
        assert result.reject_reason.startswith("file_too_large:")
