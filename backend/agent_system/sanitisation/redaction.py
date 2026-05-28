"""Vision pre-redaction pipeline (P6 — task 1.3.3).

Public API:  redact_image(image_bytes: bytes, *, padding: int = 4) -> VisionRedactionResult

Runs OCR on a sanitised image (output of 1.3.2), detects text regions, and
pixel-blacks-out every line bounding box before the image is forwarded to a
vision LLM.

Defense target: Attack #6 — adversarial text overlaid on an image to steer
vision models ("ignore previous instructions").

Two tesseract sweeps are used simultaneously via image_to_data:
  - Line-level  (level 4): gap-free bounding box covers the entire line → blackout.
  - Word-level  (level 5): word text + confidence → audit TextRegion + OCR text stream.

Line-level boxes are used for blackout (not word-level) to prevent inter-word
gaps from leaking instructions to the vision model.

Extra `padding` pixels (default 4, 2 extra at bottom for descenders) are added
around each redact box.

OCR text is routed as a separate PUBLIC+UNTRUSTED labeled stream to the parser
LLM (P1 — dual-LLM separation).

Raises OcrUnavailableError if tesseract is not installed — never silently
returns an unredacted image.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageDraw

from agent_system.ifc.labels import Labeled
from agent_system.sanitisation.text import sanitise

CONFIDENCE_THRESHOLD = 60.0


class OcrUnavailableError(RuntimeError):
    """Raised when tesseract binary is missing or pytesseract cannot invoke it."""


@dataclass(frozen=True)
class TextRegion:
    """A single confident word detected by OCR (word-level, level 5)."""

    text: str
    left: int
    top: int
    width: int
    height: int
    confidence: float


@dataclass(frozen=True)
class RedactBox:
    """A line-level bounding box used to black out a line of text."""

    left: int
    top: int
    right: int
    bottom: int


@dataclass(frozen=True)
class VisionRedactionResult:
    """Result of redact_image().

    redacted_bytes is always a PNG regardless of input format.
    regions are word-level; region_count counts the line-level redact boxes applied.
    labeled_ocr_text carries the OCR text stream for the parser LLM (PUBLIC+UNTRUSTED).
    """

    redacted_bytes: bytes
    redacted_format: str          # always "PNG"
    region_count: int             # number of line-level boxes blacked out
    regions: tuple[TextRegion, ...]  # word-level detections for audit
    ocr_text: str                 # raw joined OCR text
    labeled_ocr_text: Labeled[str]  # PUBLIC+UNTRUSTED, for parser LLM
    width: int
    height: int
    findings: tuple[str, ...]


def _parse_ocr_data(
    data: dict, threshold: float
) -> tuple[list[TextRegion], list[RedactBox]]:
    """Split tesseract output into word-level TextRegions and line-level RedactBoxes.

    Only words with confidence >= threshold are collected.  A line box is included
    iff at least one of its words passed the threshold — this ensures we only blank
    lines that actually contain readable text.
    """
    levels = data["level"]
    n = len(levels)

    text_regions: list[TextRegion] = []
    confident_line_keys: set[tuple[int, int, int]] = set()

    for i in range(n):
        if levels[i] != 5:
            continue
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            continue
        text = str(data["text"][i]).strip()
        if conf >= threshold and text:
            text_regions.append(
                TextRegion(
                    text=text,
                    left=int(data["left"][i]),
                    top=int(data["top"][i]),
                    width=int(data["width"][i]),
                    height=int(data["height"][i]),
                    confidence=conf,
                )
            )
            confident_line_keys.add(
                (int(data["block_num"][i]), int(data["par_num"][i]), int(data["line_num"][i]))
            )

    redact_boxes: list[RedactBox] = []
    for i in range(n):
        if levels[i] != 4:
            continue
        line_key = (
            int(data["block_num"][i]),
            int(data["par_num"][i]),
            int(data["line_num"][i]),
        )
        if line_key in confident_line_keys:
            left = int(data["left"][i])
            top = int(data["top"][i])
            w = int(data["width"][i])
            h = int(data["height"][i])
            redact_boxes.append(RedactBox(left=left, top=top, right=left + w, bottom=top + h))

    return text_regions, redact_boxes


def _run_ocr(
    img: Image.Image, threshold: float = CONFIDENCE_THRESHOLD
) -> tuple[list[TextRegion], list[RedactBox]]:
    """Invoke tesseract via pytesseract; raises OcrUnavailableError on any failure."""
    try:
        import pytesseract
        from pytesseract import Output
    except ImportError as exc:
        raise OcrUnavailableError(f"pytesseract not installed: {exc}") from exc

    try:
        data = pytesseract.image_to_data(img, output_type=Output.DICT)
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrUnavailableError(f"tesseract binary not found: {exc}") from exc
    except Exception as exc:
        raise OcrUnavailableError(f"tesseract error: {exc}") from exc

    return _parse_ocr_data(data, threshold)


def redact_image(image_bytes: bytes, *, padding: int = 4) -> VisionRedactionResult:
    """OCR the image, black-out every detected line box, return a redacted PNG.

    padding is added to all sides of each redact box; an extra 2 pixels is added
    to the bottom to cover descenders (g, p, y, etc.).

    Raises OcrUnavailableError if tesseract is unavailable — never returns an
    unredacted image silently.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = img.size

    text_regions, redact_boxes = _run_ocr(img)

    draw = ImageDraw.Draw(img)
    findings: list[str] = []

    for box in redact_boxes:
        x0 = max(0, box.left - padding)
        y0 = max(0, box.top - padding)
        x1 = min(width, box.right + padding)
        y1 = min(height, box.bottom + padding + 2)  # +2 for descenders
        if x0 < x1 and y0 < y1:
            draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0))

    if redact_boxes:
        findings.append(f"text_regions_redacted:{len(redact_boxes)}")

    ocr_text = " ".join(r.text for r in text_regions)
    sanitise_result = sanitise(ocr_text)
    findings.extend(sanitise_result.detections)

    buf = io.BytesIO()
    img.save(buf, format="PNG")

    return VisionRedactionResult(
        redacted_bytes=buf.getvalue(),
        redacted_format="PNG",
        region_count=len(redact_boxes),
        regions=tuple(text_regions),
        ocr_text=ocr_text,
        labeled_ocr_text=sanitise_result.labeled,
        width=width,
        height=height,
        findings=tuple(findings),
    )
