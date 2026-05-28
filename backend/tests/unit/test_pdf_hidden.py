"""Unit tests for the PDF hidden-content detector (task 1.3.4).

Tests cover:
  - _normalise_channels / _is_near_white helpers across all pdfplumber color formats
  - detect_hidden_content with adversarial CharData for each attack surface:
      white_on_white, micro_font, off_page
  - Mixed multi-attack scenarios and deduplication
  - Non-CLEAN PDFParseResult short-circuit
  - Whitespace character skipping
  - labeled_hidden_text IFC labeling (PUBLIC+UNTRUSTED)
"""
from __future__ import annotations

import pytest

from agent_system.ifc.labels import DataLabel
from agent_system.sanitisation.pdf import CharData, PageData, PDFParseResult
from agent_system.sanitisation.pdf_hidden import (
    HiddenContentFinding,
    HiddenContentResult,
    MICRO_FONT_THRESHOLD,
    _is_near_white,
    _normalise_channels,
    detect_hidden_content,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _char(
    text: str = "A",
    *,
    x0: float = 10.0,
    y0: float = 10.0,
    x1: float = 20.0,
    y1: float = 20.0,
    page_width: float = 612.0,
    page_height: float = 792.0,
    font_size: float = 12.0,
    font_name: str = "Helvetica",
    non_stroking_color: object = None,
) -> CharData:
    return CharData(
        text=text,
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        page_width=page_width,
        page_height=page_height,
        font_size=font_size,
        font_name=font_name,
        non_stroking_color=non_stroking_color,
    )


def _page(chars: list[CharData], page_number: int = 1) -> PageData:
    text = "".join(ch.text for ch in chars)
    return PageData(page_number=page_number, text=text, chars=tuple(chars))


def _clean_result(pages: list[PageData]) -> PDFParseResult:
    from agent_system.ifc.labels import DataLabel, Label, Labeled
    label = Label(level=DataLabel.PUBLIC, untrusted=True)
    all_text = "".join(p.text for p in pages)
    labeled_text = Labeled(value=f"<untrusted>{all_text}</untrusted>", label=label)
    return PDFParseResult(
        status="CLEAN",
        page_count=len(pages),
        pages=tuple(pages),
        findings=(),
        reject_reason=None,
        labeled_text=labeled_text,
    )


def _rejected_result() -> PDFParseResult:
    return PDFParseResult(
        status="REJECTED",
        page_count=0,
        pages=(),
        findings=(),
        reject_reason="test_rejection",
        labeled_text=None,
    )


def _error_result() -> PDFParseResult:
    return PDFParseResult(
        status="ERROR",
        page_count=0,
        pages=(),
        findings=(),
        reject_reason=None,
        labeled_text=None,
    )


# ---------------------------------------------------------------------------
# _normalise_channels
# ---------------------------------------------------------------------------


class TestNormaliseChannels:
    def test_none_returns_none(self):
        assert _normalise_channels(None) is None

    def test_scalar_float_below_1(self):
        result = _normalise_channels(0.95)
        assert result == pytest.approx([0.95])

    def test_scalar_int_255_normalised(self):
        result = _normalise_channels(255)
        assert result == pytest.approx([1.0])

    def test_scalar_int_0(self):
        result = _normalise_channels(0)
        assert result == pytest.approx([0.0])

    def test_rgb_tuple_float(self):
        result = _normalise_channels((1.0, 1.0, 1.0))
        assert result == pytest.approx([1.0, 1.0, 1.0])

    def test_rgb_list_float(self):
        result = _normalise_channels([0.95, 0.92, 0.91])
        assert result == pytest.approx([0.95, 0.92, 0.91])

    def test_rgb_0_255_integers(self):
        result = _normalise_channels([255, 255, 255])
        assert result is not None
        assert all(abs(c - 1.0) < 0.01 for c in result)

    def test_cmyk_tuple(self):
        result = _normalise_channels((0.0, 0.0, 0.0, 0.0))
        assert result == pytest.approx([0.0, 0.0, 0.0, 0.0])

    def test_grayscale_list(self):
        result = _normalise_channels([1.0])
        assert result == pytest.approx([1.0])

    def test_nested_rgb_list(self):
        result = _normalise_channels([[0.9, 0.9, 0.9]])
        assert result == pytest.approx([0.9, 0.9, 0.9])

    def test_empty_list_returns_none(self):
        assert _normalise_channels([]) is None

    def test_unrecognised_type_returns_none(self):
        assert _normalise_channels("white") is None

    def test_non_numeric_elements_returns_none(self):
        assert _normalise_channels(["a", "b", "c"]) is None

    def test_scalar_boundary_1_5(self):
        # Value exactly 1.5 — treated as 0–1 range (not 0–255), returned as-is
        result = _normalise_channels(1.5)
        assert result == pytest.approx([1.5])

    def test_scalar_above_1_5_normalised(self):
        result = _normalise_channels(200)
        assert result is not None
        assert result[0] == pytest.approx(200 / 255.0)


# ---------------------------------------------------------------------------
# _is_near_white
# ---------------------------------------------------------------------------


class TestIsNearWhite:
    def test_none_is_not_near_white(self):
        assert _is_near_white(None) is False

    def test_gray_white_scalar(self):
        assert _is_near_white(1.0) is True

    def test_gray_near_white_scalar(self):
        assert _is_near_white(0.95) is True

    def test_gray_below_threshold(self):
        assert _is_near_white(0.5) is False

    def test_rgb_white(self):
        assert _is_near_white([1.0, 1.0, 1.0]) is True

    def test_rgb_near_white(self):
        assert _is_near_white([0.95, 0.92, 0.91]) is True

    def test_rgb_one_channel_below_threshold(self):
        assert _is_near_white([1.0, 1.0, 0.5]) is False

    def test_rgb_black(self):
        assert _is_near_white([0.0, 0.0, 0.0]) is False

    def test_cmyk_white(self):
        assert _is_near_white([0.0, 0.0, 0.0, 0.0]) is True

    def test_cmyk_near_white(self):
        assert _is_near_white([0.05, 0.0, 0.0, 0.0]) is True

    def test_cmyk_one_channel_over_threshold(self):
        assert _is_near_white([0.0, 0.0, 0.0, 0.5]) is False

    def test_cmyk_black(self):
        assert _is_near_white([0.0, 0.0, 0.0, 1.0]) is False

    def test_0_255_white(self):
        assert _is_near_white([255, 255, 255]) is True

    def test_0_255_near_white(self):
        # 240/255 ≈ 0.941 ≥ 0.9
        assert _is_near_white([240, 240, 240]) is True

    def test_0_255_below_threshold(self):
        # 200/255 ≈ 0.784 < 0.9
        assert _is_near_white([200, 200, 200]) is False

    def test_nested_rgb_white(self):
        assert _is_near_white([[1.0, 1.0, 1.0]]) is True

    def test_2_channel_returns_false(self):
        assert _is_near_white([1.0, 1.0]) is False

    def test_unrecognised_type_returns_false(self):
        assert _is_near_white("white") is False


# ---------------------------------------------------------------------------
# Non-CLEAN result short-circuit
# ---------------------------------------------------------------------------


class TestNonCleanResult:
    def test_rejected_returns_empty(self):
        result = detect_hidden_content(_rejected_result())
        assert result.has_hidden_content is False
        assert result.hidden_char_count == 0
        assert result.findings == ()
        assert result.hidden_text == ""
        assert result.labeled_hidden_text is None

    def test_error_returns_empty(self):
        result = detect_hidden_content(_error_result())
        assert result.has_hidden_content is False
        assert result.hidden_char_count == 0
        assert result.findings == ()
        assert result.hidden_text == ""
        assert result.labeled_hidden_text is None

    def test_returns_hidden_content_result_type(self):
        assert isinstance(detect_hidden_content(_rejected_result()), HiddenContentResult)


# ---------------------------------------------------------------------------
# Clean PDF — no hidden content
# ---------------------------------------------------------------------------


class TestCleanPdfNoHiddenContent:
    def test_normal_black_text_no_findings(self):
        chars = [
            _char("H", non_stroking_color=(0.0, 0.0, 0.0)),
            _char("i", non_stroking_color=(0.0, 0.0, 0.0), font_size=12.0),
        ]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.has_hidden_content is False
        assert result.findings == ()
        assert result.hidden_char_count == 0

    def test_empty_page_no_findings(self):
        result = detect_hidden_content(_clean_result([_page([])]))
        assert result.has_hidden_content is False

    def test_none_color_not_flagged(self):
        chars = [_char("X", non_stroking_color=None, font_size=12.0)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.has_hidden_content is False


# ---------------------------------------------------------------------------
# Whitespace skipping
# ---------------------------------------------------------------------------


class TestWhitespaceSkipping:
    def test_space_with_white_color_not_flagged(self):
        chars = [_char(" ", non_stroking_color=[1.0, 1.0, 1.0])]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.has_hidden_content is False

    def test_newline_with_micro_font_not_flagged(self):
        chars = [_char("\n", font_size=0.5)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.has_hidden_content is False

    def test_tab_off_page_not_flagged(self):
        chars = [_char("\t", x0=-5.0, x1=-1.0)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.has_hidden_content is False


# ---------------------------------------------------------------------------
# White-on-white attack
# ---------------------------------------------------------------------------


class TestWhiteOnWhite:
    def test_white_rgb_text_detected(self):
        chars = [_char("X", non_stroking_color=[1.0, 1.0, 1.0])]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.has_hidden_content is True
        kinds = [f.kind for f in result.findings]
        assert "white_on_white" in kinds

    def test_near_white_rgb_detected(self):
        chars = [_char("Y", non_stroking_color=[0.95, 0.92, 0.91])]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.has_hidden_content is True

    def test_cmyk_white_detected(self):
        chars = [_char("Z", non_stroking_color=[0.0, 0.0, 0.0, 0.0])]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.has_hidden_content is True

    def test_grayscale_white_scalar_detected(self):
        chars = [_char("A", non_stroking_color=1.0)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.has_hidden_content is True

    def test_gray_below_threshold_not_flagged(self):
        chars = [_char("B", non_stroking_color=0.5)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.has_hidden_content is False

    def test_finding_contains_color_sample(self):
        chars = [_char("C", non_stroking_color=[1.0, 1.0, 1.0])]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        ww = [f for f in result.findings if f.kind == "white_on_white"]
        assert len(ww) == 1
        assert "color_sample" in ww[0].detail

    def test_char_count_in_finding(self):
        chars = [
            _char("A", non_stroking_color=[1.0, 1.0, 1.0]),
            _char("B", non_stroking_color=[0.95, 0.93, 0.91]),
        ]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        ww = [f for f in result.findings if f.kind == "white_on_white"]
        assert ww[0].char_count == 2

    def test_white_text_included_in_hidden_text(self):
        chars = [_char("S", non_stroking_color=[1.0, 1.0, 1.0])]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert "S" in result.hidden_text

    def test_0_255_white_detected(self):
        chars = [_char("W", non_stroking_color=[255, 255, 255])]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.has_hidden_content is True


# ---------------------------------------------------------------------------
# Micro-font attack
# ---------------------------------------------------------------------------


class TestMicroFont:
    def test_micro_font_below_threshold_detected(self):
        chars = [_char("M", font_size=0.5)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.has_hidden_content is True
        kinds = [f.kind for f in result.findings]
        assert "micro_font" in kinds

    def test_font_size_zero_not_detected(self):
        # pdfplumber emits size=0 for malformed text states; must not flag these
        chars = [_char("N", font_size=0.0)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        micro = [f for f in result.findings if f.kind == "micro_font"]
        assert micro == []

    def test_font_size_at_threshold_not_detected(self):
        chars = [_char("O", font_size=MICRO_FONT_THRESHOLD)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        micro = [f for f in result.findings if f.kind == "micro_font"]
        assert micro == []

    def test_font_size_just_below_threshold_detected(self):
        chars = [_char("P", font_size=MICRO_FONT_THRESHOLD - 0.001)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        micro = [f for f in result.findings if f.kind == "micro_font"]
        assert len(micro) == 1

    def test_finding_contains_min_size(self):
        chars = [_char("Q", font_size=0.3), _char("R", font_size=0.7)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        micro = [f for f in result.findings if f.kind == "micro_font"]
        assert "min_size" in micro[0].detail
        assert "0.3" in micro[0].detail

    def test_micro_font_text_in_hidden_text(self):
        chars = [_char("T", font_size=0.1)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert "T" in result.hidden_text

    def test_normal_font_size_not_detected(self):
        chars = [_char("U", font_size=12.0)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.has_hidden_content is False


# ---------------------------------------------------------------------------
# Off-page attack
# ---------------------------------------------------------------------------


class TestOffPage:
    def test_negative_x0_detected(self):
        chars = [_char("V", x0=-5.0, x1=5.0)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        kinds = [f.kind for f in result.findings]
        assert "off_page" in kinds

    def test_negative_y0_detected(self):
        chars = [_char("W", y0=-10.0, y1=0.0)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        kinds = [f.kind for f in result.findings]
        assert "off_page" in kinds

    def test_x1_beyond_page_width_detected(self):
        chars = [_char("X", x0=600.0, x1=620.0, page_width=612.0)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        kinds = [f.kind for f in result.findings]
        assert "off_page" in kinds

    def test_y1_beyond_page_height_detected(self):
        chars = [_char("Y", y0=780.0, y1=800.0, page_height=792.0)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        kinds = [f.kind for f in result.findings]
        assert "off_page" in kinds

    def test_on_page_not_flagged(self):
        chars = [_char("Z", x0=10.0, y0=10.0, x1=20.0, y1=20.0,
                        page_width=612.0, page_height=792.0)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        off = [f for f in result.findings if f.kind == "off_page"]
        assert off == []

    def test_zero_page_dimensions_not_flagged(self):
        # page_width=0 / page_height=0 means dimensions unknown — skip check
        chars = [_char("A", x0=-1.0, y0=-1.0, page_width=0.0, page_height=0.0)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        off = [f for f in result.findings if f.kind == "off_page"]
        assert off == []

    def test_finding_contains_coordinates(self):
        chars = [_char("B", x0=-5.0, y0=10.0, x1=5.0, y1=20.0)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        off = [f for f in result.findings if f.kind == "off_page"]
        assert len(off) == 1
        assert "-5.0" in off[0].detail or "-5" in off[0].detail

    def test_off_page_text_in_hidden_text(self):
        chars = [_char("C", x0=-5.0, x1=5.0)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert "C" in result.hidden_text


# ---------------------------------------------------------------------------
# Multi-page
# ---------------------------------------------------------------------------


class TestMultiPage:
    def test_findings_span_multiple_pages(self):
        page1 = _page([_char("A", non_stroking_color=[1.0, 1.0, 1.0])], page_number=1)
        page2 = _page([_char("B", font_size=0.5)], page_number=2)
        result = detect_hidden_content(_clean_result([page1, page2]))
        assert result.has_hidden_content is True
        kinds = {f.kind for f in result.findings}
        assert "white_on_white" in kinds
        assert "micro_font" in kinds

    def test_finding_page_numbers_correct(self):
        page1 = _page([_char("A", non_stroking_color=[1.0, 1.0, 1.0])], page_number=1)
        page3 = _page([_char("B", font_size=0.5)], page_number=3)
        result = detect_hidden_content(_clean_result([page1, page3]))
        ww = [f for f in result.findings if f.kind == "white_on_white"]
        mf = [f for f in result.findings if f.kind == "micro_font"]
        assert ww[0].page_number == 1
        assert mf[0].page_number == 3

    def test_hidden_text_spans_pages(self):
        page1 = _page([_char("A", non_stroking_color=[1.0, 1.0, 1.0])], page_number=1)
        page2 = _page([_char("B", font_size=0.5)], page_number=2)
        result = detect_hidden_content(_clean_result([page1, page2]))
        assert "A" in result.hidden_text
        assert "B" in result.hidden_text


# ---------------------------------------------------------------------------
# Mixed attacks and deduplication
# ---------------------------------------------------------------------------


class TestMixedAttacksAndDedup:
    def test_all_three_attack_types_detected(self):
        chars = [
            _char("A", non_stroking_color=[1.0, 1.0, 1.0]),
            _char("B", font_size=0.5),
            _char("C", x0=-5.0, x1=5.0),
        ]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        kinds = {f.kind for f in result.findings}
        assert kinds == {"white_on_white", "micro_font", "off_page"}

    def test_char_matching_two_criteria_counted_once(self):
        # A char that is both white AND micro-font should appear once in hidden_text
        ch = _char("D", non_stroking_color=[1.0, 1.0, 1.0], font_size=0.5)
        result = detect_hidden_content(_clean_result([_page([ch])]))
        assert result.hidden_char_count == 1
        assert result.hidden_text.count("D") == 1

    def test_char_matching_all_three_counted_once(self):
        ch = _char(
            "E",
            non_stroking_color=[1.0, 1.0, 1.0],
            font_size=0.5,
            x0=-5.0,
            x1=5.0,
        )
        result = detect_hidden_content(_clean_result([_page([ch])]))
        assert result.hidden_char_count == 1

    def test_hidden_char_count_total(self):
        chars = [
            _char("F", non_stroking_color=[1.0, 1.0, 1.0]),
            _char("G", font_size=0.5),
            _char("H", x0=-1.0),
        ]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.hidden_char_count == 3

    def test_original_char_order_preserved(self):
        chars = [
            _char("X", non_stroking_color=[1.0, 1.0, 1.0]),
            _char("Y", font_size=0.5),
            _char("Z", x0=-5.0, x1=5.0),
        ]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.hidden_text == "XYZ"


# ---------------------------------------------------------------------------
# IFC labeling
# ---------------------------------------------------------------------------


class TestIFCLabeling:
    def test_labeled_hidden_text_is_public_untrusted(self):
        chars = [_char("A", non_stroking_color=[1.0, 1.0, 1.0])]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.labeled_hidden_text is not None
        assert result.labeled_hidden_text.label.level == DataLabel.PUBLIC
        assert result.labeled_hidden_text.label.untrusted is True

    def test_labeled_hidden_text_wrapped_in_untrusted_tags(self):
        chars = [_char("B", font_size=0.5)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.labeled_hidden_text is not None
        assert result.labeled_hidden_text.value.startswith("<untrusted>")
        assert result.labeled_hidden_text.value.endswith("</untrusted>")

    def test_no_hidden_content_labeled_text_is_none(self):
        chars = [_char("C", non_stroking_color=(0.0, 0.0, 0.0), font_size=12.0)]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.labeled_hidden_text is None

    def test_labeled_hidden_text_contains_hidden_chars(self):
        chars = [_char("S", non_stroking_color=[1.0, 1.0, 1.0])]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.labeled_hidden_text is not None
        assert "S" in result.labeled_hidden_text.value


# ---------------------------------------------------------------------------
# Result structure invariants
# ---------------------------------------------------------------------------


class TestResultStructure:
    def test_result_is_frozen(self):
        result = detect_hidden_content(_clean_result([_page([])]))
        with pytest.raises((AttributeError, TypeError)):
            result.has_hidden_content = True  # type: ignore[misc]

    def test_findings_is_tuple(self):
        result = detect_hidden_content(_clean_result([_page([])]))
        assert isinstance(result.findings, tuple)

    def test_finding_is_frozen(self):
        chars = [_char("A", non_stroking_color=[1.0, 1.0, 1.0])]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert len(result.findings) > 0
        finding = result.findings[0]
        with pytest.raises((AttributeError, TypeError)):
            finding.kind = "mutated"  # type: ignore[misc]

    def test_finding_kinds_valid(self):
        valid_kinds = {"white_on_white", "micro_font", "off_page"}
        chars = [
            _char("A", non_stroking_color=[1.0, 1.0, 1.0]),
            _char("B", font_size=0.5),
            _char("C", x0=-1.0),
        ]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        for f in result.findings:
            assert f.kind in valid_kinds

    def test_hidden_char_count_matches_hidden_text_length(self):
        chars = [
            _char("A", non_stroking_color=[1.0, 1.0, 1.0]),
            _char("B", non_stroking_color=[1.0, 1.0, 1.0]),
        ]
        result = detect_hidden_content(_clean_result([_page(chars)]))
        assert result.hidden_char_count == len(result.hidden_text)
