"""Hidden-content detector for PDF parse results (task 1.3.4).

Public API:  detect_hidden_content(result: PDFParseResult) -> HiddenContentResult

Operates on the chars array produced by parse_pdf() (task 1.3.1).
No Docker or subprocess — pure analysis of already-extracted per-character
metadata from the sandbox.

Three attack surfaces are checked per non-whitespace character:

  white_on_white — non_stroking_color is near-white (≥ 0.9 per channel in
                    RGB/Gray, ≤ 0.1 per channel in CMYK).  Handles all color
                    space representations pdfplumber can emit (tuple, nested
                    list, integer 0-255 range, single scalar).

  micro_font     — font_size ∈ (0, MICRO_FONT_THRESHOLD).  Characters
                    rendered < 1 pt are typically invisible to human readers.
                    font_size == 0 is excluded; pdfplumber occasionally emits
                    size=0 for chars in malformed text states.

  off_page       — any coordinate outside [0, page_dimension].  Acrobat
                    includes off-canvas text in copy-paste and full-text
                    search; human readers never see it.

All three are detection signals only (never blocks — P1 dual-LLM is the primary
defence).  Hidden chars are extracted and run through the text sanitisation
pipeline so their content is processed rather than silently dropped.
"""
from __future__ import annotations

from dataclasses import dataclass

from agent_system.ifc.labels import Labeled
from agent_system.sanitisation.pdf import CharData, PDFParseResult
from agent_system.sanitisation.text import sanitise

MICRO_FONT_THRESHOLD: float = 1.0   # pt — below this is considered microscopic
_NEAR_WHITE_MIN: float = 0.9        # RGB/Gray channel value ≥ this → near-white
_NEAR_WHITE_CMYK_MAX: float = 0.1   # CMYK channel value ≤ this → near-zero ink (white)


def _normalise_channels(color: object) -> list[float] | None:
    """Return [0.0, 1.0]-normalised channel values from any pdfplumber color format.

    pdfplumber can emit any of:
      - None (unset)
      - A scalar float or int (DeviceGray)
      - A list or tuple of 1/3/4 values  (Gray / RGB / CMYK)
      - A singly-nested list  [[r, g, b]]  (unwrapped Pattern space)
      - Integer values in 0-255 range (normalised here)
    Returns None if the format is unrecognised.
    """
    if color is None:
        return None

    # Scalar grayscale (float/int, not wrapped in a list)
    if isinstance(color, (int, float)):
        v = float(color)
        return [v / 255.0 if v > 1.5 else v]

    if not isinstance(color, (list, tuple)):
        return None

    # Unwrap one level of nesting: [[r, g, b]] → [r, g, b]
    if len(color) == 1 and isinstance(color[0], (list, tuple)):
        color = color[0]

    if not color:
        return None

    try:
        channels = [float(c) for c in color]
    except (TypeError, ValueError):
        return None

    # Detect 0-255 integer range: normalise to 0-1
    if any(c > 1.5 for c in channels):
        channels = [c / 255.0 for c in channels]

    return channels


def _is_near_white(color: object) -> bool:
    """Return True if *color* represents near-white in any PDF color space."""
    channels = _normalise_channels(color)
    if channels is None:
        return False
    n = len(channels)
    if n == 1:
        return channels[0] >= _NEAR_WHITE_MIN
    if n == 3:
        return all(c >= _NEAR_WHITE_MIN for c in channels)
    if n == 4:
        # CMYK: white = near-zero ink on all channels
        return all(c <= _NEAR_WHITE_CMYK_MAX for c in channels)
    return False


@dataclass(frozen=True)
class HiddenContentFinding:
    """A single hidden-content detection on one page."""

    kind: str          # "white_on_white" | "micro_font" | "off_page"
    page_number: int
    char_count: int
    detail: str        # human-readable detail for the audit log


@dataclass(frozen=True)
class HiddenContentResult:
    """Result of detect_hidden_content().

    has_hidden_content is True iff at least one hidden char was found.
    labeled_hidden_text is None when has_hidden_content is False.
    """

    has_hidden_content: bool
    hidden_char_count: int
    findings: tuple[HiddenContentFinding, ...]
    hidden_text: str
    labeled_hidden_text: Labeled[str] | None


def _analyze_page(
    page_number: int,
    chars: tuple[CharData, ...],
) -> tuple[list[HiddenContentFinding], list[CharData]]:
    """Return (findings, hidden_chars) for a single page.

    A char qualifying under multiple detection types is included once in
    hidden_chars.  Dedup is by object identity (id) because non_stroking_color
    may be a list and lists are not hashable.
    """
    white_on_white: list[CharData] = []
    micro_font: list[CharData] = []
    off_page: list[CharData] = []

    for ch in chars:
        if not ch.text.strip():
            continue  # whitespace is expected to be invisible — skip

        if _is_near_white(ch.non_stroking_color):
            white_on_white.append(ch)

        if 0 < ch.font_size < MICRO_FONT_THRESHOLD:
            micro_font.append(ch)

        if (
            ch.page_width > 0
            and ch.page_height > 0
            and (
                ch.x0 < 0
                or ch.y0 < 0
                or ch.x1 > ch.page_width
                or ch.y1 > ch.page_height
            )
        ):
            off_page.append(ch)

    findings: list[HiddenContentFinding] = []
    # Dedup by object identity: non_stroking_color may be a list (unhashable),
    # so we cannot use set[CharData] directly.  All chars come from the same
    # input tuple so id() values are stable and unique within this call.
    all_hidden_ids: set[int] = set()

    if white_on_white:
        findings.append(
            HiddenContentFinding(
                kind="white_on_white",
                page_number=page_number,
                char_count=len(white_on_white),
                detail=f"color_sample={white_on_white[0].non_stroking_color}",
            )
        )
        for ch in white_on_white:
            all_hidden_ids.add(id(ch))

    if micro_font:
        min_size = min(ch.font_size for ch in micro_font)
        findings.append(
            HiddenContentFinding(
                kind="micro_font",
                page_number=page_number,
                char_count=len(micro_font),
                detail=f"min_size={min_size}",
            )
        )
        for ch in micro_font:
            all_hidden_ids.add(id(ch))

    if off_page:
        c0 = off_page[0]
        findings.append(
            HiddenContentFinding(
                kind="off_page",
                page_number=page_number,
                char_count=len(off_page),
                detail=f"example=({c0.x0},{c0.y0},{c0.x1},{c0.y1})",
            )
        )
        for ch in off_page:
            all_hidden_ids.add(id(ch))

    # Preserve original char order from the page
    hidden_ordered = [ch for ch in chars if id(ch) in all_hidden_ids]
    return findings, hidden_ordered


def detect_hidden_content(result: PDFParseResult) -> HiddenContentResult:
    """Analyse a PDFParseResult for hidden-content attack vectors.

    Returns an empty HiddenContentResult if result.status != "CLEAN" — errors
    and rejections are handled upstream; there is nothing to scan.
    """
    if result.status != "CLEAN":
        return HiddenContentResult(
            has_hidden_content=False,
            hidden_char_count=0,
            findings=(),
            hidden_text="",
            labeled_hidden_text=None,
        )

    all_findings: list[HiddenContentFinding] = []
    all_hidden: list[CharData] = []

    for page in result.pages:
        page_findings, page_hidden = _analyze_page(page.page_number, page.chars)
        all_findings.extend(page_findings)
        all_hidden.extend(page_hidden)

    if not all_findings:
        return HiddenContentResult(
            has_hidden_content=False,
            hidden_char_count=0,
            findings=(),
            hidden_text="",
            labeled_hidden_text=None,
        )

    hidden_text = "".join(ch.text for ch in all_hidden)
    sanitise_result = sanitise(hidden_text)

    return HiddenContentResult(
        has_hidden_content=True,
        hidden_char_count=len(all_hidden),
        findings=tuple(all_findings),
        hidden_text=hidden_text,
        labeled_hidden_text=sanitise_result.labeled,
    )
