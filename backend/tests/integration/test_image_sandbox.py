"""Integration tests for the image sandbox container (task 1.3.2).

Requires:
  - Docker daemon accessible on the host socket.
  - `secureclaim-image-sandbox:latest` already built (`make build-image-sandbox`).
  - Pillow installed in the dev environment (`uv sync --group dev`).

Run via:
  make test-image-sandbox

The `test_no_network_access` test verifies the Phase 1 milestone:
"Sandboxes have no network access (verified)."
"""
from __future__ import annotations

import io
import json
import subprocess

import pytest

from agent_system.sanitisation.image import (
    SANDBOX_IMAGE,
    SANDBOX_TIMEOUT_S,
    _DOCKER_FLAGS,
    sanitise_image,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers / skip guard
# ---------------------------------------------------------------------------


def _docker_available() -> bool:
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _image_exists() -> bool:
    try:
        r = subprocess.run(
            ["docker", "image", "inspect", SANDBOX_IMAGE],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


requires_sandbox = pytest.mark.skipif(
    not (_docker_available() and _image_exists()),
    reason=f"Docker unavailable or image {SANDBOX_IMAGE} not built "
           "(run: make build-image-sandbox)",
)


def _make_white_png(width: int = 64, height: int = 64) -> bytes:
    """Generate a small solid-white PNG using Pillow."""
    from PIL import Image as PILImage

    img = PILImage.new("RGB", (width, height), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg(width: int = 64, height: int = 64) -> bytes:
    """Generate a small solid-colour JPEG using Pillow."""
    from PIL import Image as PILImage

    img = PILImage.new("RGB", (width, height), color=(100, 149, 237))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _make_png_with_exif() -> bytes:
    """Generate a PNG that carries fake metadata (checked for stripping)."""
    from PIL import Image as PILImage, PngImagePlugin

    img = PILImage.new("RGB", (32, 32), color=(64, 128, 192))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Comment", "EXIF_TEST_MARKER_12345")
    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=meta)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Sandbox isolation (mirrors 1.3.1 probes)
# ---------------------------------------------------------------------------


@requires_sandbox
class TestNetworkIsolation:
    def test_no_network_access(self):
        """Phase 1 milestone: sandbox must have no network access."""
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
            ["docker", "run", "--entrypoint=python3"]
            + _DOCKER_FLAGS
            + [SANDBOX_IMAGE, "-c", probe_script]
        )
        result = subprocess.run(cmd, capture_output=True, timeout=SANDBOX_TIMEOUT_S)
        assert result.returncode != 0, (
            "CRITICAL: sandbox container successfully made a network connection. "
            "--network=none is not being applied."
        )

    def test_filesystem_is_read_only(self):
        """Container rootfs must be immutable."""
        probe_script = (
            "import sys\n"
            "try:\n"
            "    open('/rootfs_probe', 'w').close()\n"
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
        assert result.returncode != 0

    def test_tmp_is_writable(self):
        """/tmp tmpfs must be writable (Pillow uses it as scratch space)."""
        probe_script = (
            "import sys, tempfile\n"
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
        assert result.returncode == 0, result.stderr.decode()

    def test_runs_as_unprivileged_user(self):
        """Container must run as uid=65534 (nobody)."""
        probe_script = "import os; print(os.getuid())"
        cmd = (
            ["docker", "run", "--entrypoint=python3"]
            + _DOCKER_FLAGS
            + [SANDBOX_IMAGE, "-c", probe_script]
        )
        result = subprocess.run(cmd, capture_output=True, timeout=SANDBOX_TIMEOUT_S)
        assert result.stdout.strip().decode() == "65534"


# ---------------------------------------------------------------------------
# End-to-end parse through real container
# ---------------------------------------------------------------------------


@requires_sandbox
class TestEndToEndParse:
    def test_white_png_clean(self):
        result = sanitise_image(_make_white_png())
        assert result.status == "CLEAN"

    def test_re_encoded_bytes_present(self):
        result = sanitise_image(_make_white_png())
        assert result.re_encoded_bytes is not None
        assert len(result.re_encoded_bytes) > 0

    def test_png_re_encoded_as_png(self):
        result = sanitise_image(_make_white_png())
        assert result.re_encoded_format == "PNG"

    def test_jpeg_re_encoded_as_jpeg(self):
        result = sanitise_image(_make_jpeg())
        assert result.re_encoded_format == "JPEG"

    def test_dimensions_correct(self):
        result = sanitise_image(_make_white_png(64, 64))
        assert result.width == 64
        assert result.height == 64

    def test_labeled_metadata_public_untrusted(self):
        from agent_system.ifc.labels import DataLabel

        result = sanitise_image(_make_white_png())
        assert result.labeled_metadata is not None
        assert result.labeled_metadata.label.untrusted is True
        assert result.labeled_metadata.label.level == DataLabel.PUBLIC

    def test_labeled_metadata_wrapped(self):
        result = sanitise_image(_make_white_png())
        assert result.labeled_metadata.value.startswith("<untrusted>")
        assert result.labeled_metadata.value.endswith("</untrusted>")

    def test_reject_reason_none_for_clean(self):
        result = sanitise_image(_make_white_png())
        assert result.reject_reason is None

    def test_findings_is_tuple(self):
        result = sanitise_image(_make_white_png())
        assert isinstance(result.findings, tuple)

    def test_re_encoded_png_is_valid_png(self):
        """Re-encoded bytes must be a parseable PNG."""
        from PIL import Image as PILImage

        result = sanitise_image(_make_white_png())
        img = PILImage.open(io.BytesIO(result.re_encoded_bytes))
        assert img.format == "PNG"

    def test_re_encoded_jpeg_is_valid_jpeg(self):
        """Re-encoded bytes must be a parseable JPEG."""
        from PIL import Image as PILImage

        result = sanitise_image(_make_jpeg())
        img = PILImage.open(io.BytesIO(result.re_encoded_bytes))
        assert img.format == "JPEG"

    def test_metadata_stripped_from_png(self):
        """Re-encoded PNG must not contain the original text metadata."""
        from PIL import Image as PILImage

        png_with_meta = _make_png_with_exif()
        result = sanitise_image(png_with_meta)
        assert result.status == "CLEAN"
        re_img = PILImage.open(io.BytesIO(result.re_encoded_bytes))
        # PIL text chunks are in .info for PNG
        assert "EXIF_TEST_MARKER_12345" not in str(re_img.info)

    def test_steg_not_flagged_for_solid_white(self):
        """Solid-colour PNG concentrates pixel values — must not be flagged."""
        result = sanitise_image(_make_white_png())
        assert result.steg_flag is False

    def test_steg_score_none_for_jpeg(self):
        """JPEG input must skip the steg heuristic (steg_score=null)."""
        result = sanitise_image(_make_jpeg())
        assert result.steg_score is None

    def test_container_exits_zero_for_clean_image(self):
        png = _make_white_png()
        cmd = ["docker", "run"] + _DOCKER_FLAGS + [SANDBOX_IMAGE]
        result = subprocess.run(
            cmd, input=png, capture_output=True, timeout=SANDBOX_TIMEOUT_S
        )
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["status"] == "CLEAN"

    def test_empty_stdin_rejected_by_container(self):
        cmd = ["docker", "run"] + _DOCKER_FLAGS + [SANDBOX_IMAGE]
        result = subprocess.run(
            cmd, input=b"", capture_output=True, timeout=SANDBOX_TIMEOUT_S
        )
        payload = json.loads(result.stdout)
        assert payload["status"] == "REJECTED"
        assert payload["reject_reason"] == "empty_input"

    def test_client_rejects_pdf_magic_bytes(self):
        result = sanitise_image(b"%PDF-1.4 fake")
        assert result.status == "REJECTED"
        assert result.reject_reason == "unsupported_format"

    def test_client_rejects_oversized(self):
        from agent_system.sanitisation.image import MAX_IMAGE_BYTES

        big = b"\x89PNG\r\n\x1a\n" + b"x" * (MAX_IMAGE_BYTES + 1)
        result = sanitise_image(big)
        assert result.status == "REJECTED"
        assert result.reject_reason.startswith("file_too_large:")
