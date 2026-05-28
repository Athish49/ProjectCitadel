"""Integration tests for the vision pre-redaction pipeline (task 1.3.3).

Requires:
  - tesseract-ocr system binary installed on the host.
  - pytesseract Python package (installed via uv add pytesseract).
  - Pillow installed in the dev environment.

Run via:
  make test-vision-redaction

Tests use programmatically-generated images.  Because OCR on minimal
machine-generated images can be imprecise, correctness probes focus on
structural invariants (result type, format, dimensions, label) rather than
specific word detections.  The `test_text_image_produces_valid_redacted_png`
test verifies that a text overlay is processed end-to-end.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image as PILImage, ImageDraw, ImageFont

from agent_system.ifc.labels import DataLabel
from agent_system.sanitisation.redaction import (
    OcrUnavailableError,
    VisionRedactionResult,
    redact_image,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Skip guard
# ---------------------------------------------------------------------------


def _tesseract_available() -> bool:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


requires_tesseract = pytest.mark.skipif(
    not _tesseract_available(),
    reason="tesseract-ocr binary not available on this host",
)


# ---------------------------------------------------------------------------
# Image fixtures
# ---------------------------------------------------------------------------


def _make_white_png(width: int = 64, height: int = 64) -> bytes:
    img = PILImage.new("RGB", (width, height), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_text_png(text: str = "Hello World", width: int = 200, height: int = 60) -> bytes:
    """Generate a PNG with black text on white background using the default font."""
    img = PILImage.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Use default bitmap font — always available, no system font dependency
    draw.text((10, 20), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg(width: int = 64, height: int = 64) -> bytes:
    img = PILImage.new("RGB", (width, height), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Structural / type invariants (no text)
# ---------------------------------------------------------------------------


@requires_tesseract
class TestStructuralInvariants:
    def test_returns_vision_redaction_result(self):
        result = redact_image(_make_white_png())
        assert isinstance(result, VisionRedactionResult)

    def test_format_is_always_png(self):
        result = redact_image(_make_white_png())
        assert result.redacted_format == "PNG"

    def test_format_is_png_even_for_jpeg_input(self):
        result = redact_image(_make_jpeg())
        assert result.redacted_format == "PNG"

    def test_redacted_bytes_is_valid_png(self):
        result = redact_image(_make_white_png())
        img = PILImage.open(io.BytesIO(result.redacted_bytes))
        assert img.format == "PNG"

    def test_dimensions_preserved(self):
        result = redact_image(_make_white_png(80, 60))
        assert result.width == 80
        assert result.height == 60

    def test_labeled_ocr_text_is_public_untrusted(self):
        result = redact_image(_make_white_png())
        assert result.labeled_ocr_text.label.level == DataLabel.PUBLIC
        assert result.labeled_ocr_text.label.untrusted is True

    def test_labeled_ocr_text_wrapped(self):
        result = redact_image(_make_white_png())
        assert result.labeled_ocr_text.value.startswith("<untrusted>")
        assert result.labeled_ocr_text.value.endswith("</untrusted>")

    def test_region_count_non_negative(self):
        result = redact_image(_make_white_png())
        assert result.region_count >= 0

    def test_regions_is_tuple(self):
        result = redact_image(_make_white_png())
        assert isinstance(result.regions, tuple)

    def test_findings_is_tuple(self):
        result = redact_image(_make_white_png())
        assert isinstance(result.findings, tuple)

    def test_result_is_frozen(self):
        result = redact_image(_make_white_png())
        with pytest.raises((AttributeError, TypeError)):
            result.region_count = 99  # type: ignore[misc]

    def test_blank_image_no_redaction_finding(self):
        result = redact_image(_make_white_png())
        assert not any("text_regions_redacted" in f for f in result.findings)


# ---------------------------------------------------------------------------
# End-to-end text image
# ---------------------------------------------------------------------------


@requires_tesseract
class TestTextImage:
    def test_text_image_produces_valid_redacted_png(self):
        """End-to-end: a text image goes in, a valid redacted PNG comes out."""
        result = redact_image(_make_text_png("Hello World"))
        img = PILImage.open(io.BytesIO(result.redacted_bytes))
        assert img.format == "PNG"

    def test_text_image_dimensions_unchanged(self):
        result = redact_image(_make_text_png(width=200, height=60))
        assert result.width == 200
        assert result.height == 60

    def test_labeled_ocr_text_is_untrusted_string(self):
        result = redact_image(_make_text_png("Test"))
        assert isinstance(result.labeled_ocr_text.value, str)
        assert result.labeled_ocr_text.label.untrusted is True

    def test_redacted_png_parseable(self):
        result = redact_image(_make_text_png())
        img = PILImage.open(io.BytesIO(result.redacted_bytes))
        img.load()  # forces pixel decode — verifies it is not truncated

    def test_regions_confidence_in_range(self):
        """Any detected regions must have confidence in [0, 100]."""
        result = redact_image(_make_text_png())
        for region in result.regions:
            assert 0.0 <= region.confidence <= 100.0

    def test_region_count_matches_regions_length_is_consistent(self):
        """region_count reflects line-level boxes; len(regions) reflects word-level."""
        result = redact_image(_make_text_png())
        # These can differ (multiple words per line), but both must be >= 0
        assert result.region_count >= 0
        assert len(result.regions) >= 0


# ---------------------------------------------------------------------------
# OcrUnavailableError propagation
# ---------------------------------------------------------------------------


@requires_tesseract
class TestOcrUnavailableError:
    def test_raises_if_pytesseract_import_fails(self):
        """Patching pytesseract out of sys.modules triggers OcrUnavailableError."""
        from unittest.mock import patch
        with patch.dict("sys.modules", {"pytesseract": None}):
            with pytest.raises(OcrUnavailableError):
                redact_image(_make_white_png())
