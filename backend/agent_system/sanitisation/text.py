"""Text sanitiser (task 1.2.6).

Every external string enters the agent pipeline through sanitise().
Four passes run in order:

  1. NFKC normalise  — collapses fullwidth/compatibility variants.
  2. Strip Cf chars  — removes zero-width chars, bidi controls, joiners.
  3. Delimiter strip — removes <untrusted>/<untrusted> tags to prevent
                        injection through the wrapping scheme.
  4. Pattern detect  — runs INJECTION_PATTERNS on the cleaned text.

The result is always wrapped in <untrusted>…</untrusted> and labeled
PUBLIC+UNTRUSTED.  Detections are signals, not blocks — the dual-LLM
architecture (P1) is the primary defence.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from agent_system.ifc.labels import DataLabel, Label, Labeled
from agent_system.sanitisation.patterns import detect_patterns

_DELIMITER_RE = re.compile(r"</?\s*untrusted\s*>", re.IGNORECASE)


@dataclass(frozen=True)
class SanitiseResult:
    labeled: Labeled[str]
    detections: list[str]
    chars_stripped: int


def sanitise(raw: str) -> SanitiseResult:
    """Sanitise an external string and return a labeled, wrapped result.

    Pure function — no I/O.
    """
    # Pass 1: NFKC normalisation
    normalised = unicodedata.normalize("NFKC", raw)

    # Pass 2: strip Unicode Cf (Format) characters
    cleaned = "".join(ch for ch in normalised if unicodedata.category(ch) != "Cf")
    chars_stripped = len(normalised) - len(cleaned)

    # Pass 3: delimiter injection — strip <untrusted> / </untrusted> tags
    detections: list[str] = []
    stripped, n_delimiters = _DELIMITER_RE.subn("", cleaned)
    if n_delimiters:
        detections.append("delimiter_injection")

    # Pass 4: pattern detection on clean text
    detections.extend(detect_patterns(stripped))

    wrapped = f"<untrusted>{stripped}</untrusted>"
    label = Label(level=DataLabel.PUBLIC, untrusted=True)
    return SanitiseResult(
        labeled=Labeled(value=wrapped, label=label),
        detections=detections,
        chars_stripped=chars_stripped,
    )
