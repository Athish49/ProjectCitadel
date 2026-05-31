"""PDF parser — runs inside the sandbox container.

Reads raw PDF bytes from stdin, writes a single JSON object to stdout.

Two-library strategy:
  - pypdf: structural threat scan (JS, embedded files, active forms,
           launch/additional actions).  pdfplumber does not surface these.
  - pdfplumber: text + per-character metadata extraction.  The chars array
                includes all fields needed for 1.3.4 hidden-content detection
                (white-on-white, micro-font, off-page) without re-parsing.

Output schema
-------------
{
  "status":        "CLEAN" | "REJECTED",
  "reject_reason": null | str,   # first threat found
  "page_count":    int,
  "pages": [
    {
      "page_number": int,         # 1-based
      "text":        str,
      "chars": [
        {
          "text": str,
          "x0": float, "y0": float, "x1": float, "y1": float,
          "page_width": float, "page_height": float,
          "font_size": float,
          "font_name": str,
          "non_stroking_color": list | null
        }
      ]
    }
  ],
  "findings": [str]   # non-fatal observations (reserved for future use)
}

On any unhandled exception the process exits with code 1 and writes a
minimal error object to stdout so the parent can distinguish sandbox
crash from parse error.
"""
from __future__ import annotations

import io
import json
import sys
from typing import Any


def _scan_threats(pdf_bytes: bytes) -> tuple[str | None, list[str]]:
    """Return (reject_reason, findings) using pypdf structural analysis."""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    findings: list[str] = []
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes), strict=False)
    except PdfReadError as exc:
        return f"parse_error:{exc}", []

    trailer = reader.trailer

    # JavaScript at document level
    if "/Names" in trailer.get("/Root", {}):
        root = trailer["/Root"]
        names = root.get("/Names", {})
        if "/JavaScript" in names:
            return "javascript", findings

    # Embedded files (file attachment or EmbeddedFile stream)
    root = trailer.get("/Root", {})
    names = root.get("/Names", {})
    if "/EmbeddedFiles" in names:
        return "embedded_file", findings

    # AcroForm with active (non-display) field actions
    acroform = root.get("/AcroForm", {})
    if acroform:
        xfa = acroform.get("/XFA")
        if xfa:
            return "xfa_form", findings
        # Check for JS actions inside form fields
        fields = acroform.get("/Fields", [])
        for field_ref in fields:
            try:
                field = field_ref.get_object() if hasattr(field_ref, "get_object") else field_ref
                for action_key in ("/AA", "/A"):
                    action = field.get(action_key, {})
                    if isinstance(action, dict) and action.get("/S") == "/JavaScript":
                        return "active_form", findings
            except Exception:
                pass

    # Document-level additional actions (/AA) with JS
    aa = root.get("/AA", {})
    if aa:
        for _trigger, action in aa.items():
            try:
                obj = action.get_object() if hasattr(action, "get_object") else action
                if isinstance(obj, dict) and obj.get("/S") == "/JavaScript":
                    return "additional_actions", findings
            except Exception:
                pass

    # Launch actions anywhere in page content streams (lightweight scan via
    # raw trailer walk is expensive; check page /AA and /Annots instead)
    for page in reader.pages:
        page_aa = page.get("/AA", {})
        for _trigger, action in page_aa.items():
            try:
                obj = action.get_object() if hasattr(action, "get_object") else action
                if isinstance(obj, dict) and obj.get("/S") in ("/Launch", "/JavaScript"):
                    return "launch_action", findings
            except Exception:
                pass
        for annot_ref in page.get("/Annots", []):
            try:
                annot = annot_ref.get_object() if hasattr(annot_ref, "get_object") else annot_ref
                action = annot.get("/A", {})
                if isinstance(action, dict):
                    s = action.get("/S", "")
                    if s in ("/Launch", "/JavaScript"):
                        return "launch_action", findings
            except Exception:
                pass

    return None, findings


def _extract_pages(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Extract text and per-character metadata using pdfplumber."""
    import pdfplumber

    pages: list[dict[str, Any]] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            pw = float(page.width)
            ph = float(page.height)
            chars: list[dict[str, Any]] = []
            for ch in page.chars:
                chars.append(
                    {
                        "text": ch.get("text", ""),
                        "x0": ch.get("x0", 0.0),
                        "y0": ch.get("y0", 0.0),
                        "x1": ch.get("x1", 0.0),
                        "y1": ch.get("y1", 0.0),
                        "page_width": pw,
                        "page_height": ph,
                        "font_size": ch.get("size", 0.0),
                        "font_name": ch.get("fontname", ""),
                        "non_stroking_color": ch.get("non_stroking_color"),
                    }
                )
            pages.append(
                {
                    "page_number": page.page_number,
                    "text": page.extract_text() or "",
                    "chars": chars,
                }
            )
    return pages


def main() -> None:
    pdf_bytes = sys.stdin.buffer.read()

    if not pdf_bytes:
        json.dump(
            {
                "status": "REJECTED",
                "reject_reason": "empty_input",
                "page_count": 0,
                "pages": [],
                "findings": [],
            },
            sys.stdout,
        )
        return

    # Structural threat scan first — abort before touching page content.
    reject_reason, findings = _scan_threats(pdf_bytes)
    if reject_reason:
        json.dump(
            {
                "status": "REJECTED",
                "reject_reason": reject_reason,
                "page_count": 0,
                "pages": [],
                "findings": findings,
            },
            sys.stdout,
        )
        return

    # Text + character extraction.
    try:
        pages = _extract_pages(pdf_bytes)
    except Exception as exc:
        json.dump(
            {
                "status": "REJECTED",
                "reject_reason": f"extract_error:{exc}",
                "page_count": 0,
                "pages": [],
                "findings": findings,
            },
            sys.stdout,
        )
        return

    json.dump(
        {
            "status": "CLEAN",
            "reject_reason": None,
            "page_count": len(pages),
            "pages": pages,
            "findings": findings,
        },
        sys.stdout,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Hard crash — write error JSON so parent gets structured output.
        json.dump(
            {
                "status": "REJECTED",
                "reject_reason": f"fatal:{exc}",
                "page_count": 0,
                "pages": [],
                "findings": [],
            },
            sys.stdout,
        )
        sys.exit(1)
