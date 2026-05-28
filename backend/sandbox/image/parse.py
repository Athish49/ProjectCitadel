"""Image parser — runs inside the sandbox container (task 1.3.2).

Reads raw image bytes from stdin, writes a single JSON object to stdout.

Processing steps (§2.5.2):
  1. Magic-byte validation — reject unrecognised formats early.
  2. Dimension / pixel-count guard — reject decompression bombs.
  3. EXIF orientation applied before metadata strip (phone photos).
  4. Metadata strip — re-create image from raw pixel data; no EXIF/XMP/IPTC.
  5. Re-encode — JPEG→JPEG (q=95, no metadata); all others→PNG (lossless).
  6. LSB chi-square steganography heuristic — detection signal only; never
     blocks.  Skipped for JPEG (lossy compression destroys LSBs).
  7. Multi-frame truncation note — frame 0 only for GIF/animated WEBP.

Output schema
-------------
{
  "status":             "CLEAN" | "REJECTED",
  "reject_reason":      null | str,
  "format":             str,            # Pillow format name of input
  "re_encoded_format":  str | null,     # "JPEG" or "PNG"
  "width":              int | null,
  "height":             int | null,
  "mode":               str | null,     # Pillow mode: RGB, RGBA, L, ...
  "steg_flag":          bool,
  "steg_score":         float | null,   # chi2_stat/dof; null if not tested
  "re_encoded_b64":     str | null,     # base64 of metadata-stripped image
  "findings":           [str]
}
"""
from __future__ import annotations

import base64
import io
import json
import sys
from collections import Counter
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

# Disable Pillow's decompression-bomb limit — we enforce our own stricter one.
Image.MAX_IMAGE_PIXELS = None

MAX_DIMENSION = 16384    # pixels on either axis
MAX_PIXELS = 40_000_000  # 40 MP total (≈ 6500×6150)

# Formats that pass through the LSB chi-square test.
# JPEG and lossy WEBP are excluded: JPEG compression randomises LSBs and
# produces false positives; there is no reliable way to detect stego after
# lossy encoding.
LOSSLESS_FORMATS = {"PNG", "GIF", "BMP", "TIFF"}

# Flag if normalised chi-square score < threshold (pairs too equalized).
LSB_STEG_THRESHOLD = 1.0


def _lsb_chi_square(img: Image.Image) -> tuple[bool, float]:
    """Chi-square LSB steganography heuristic.

    Computes how equalized consecutive pixel-value pairs (2k, 2k+1) are
    across all RGB channels.  For natural images the pairs are unequal
    (large score).  LSB-substitution steganography equalizes them (small
    score).

    Returns (flagged, score) where score = chi2_stat / dof.
    Flagged when score < LSB_STEG_THRESHOLD.
    """
    raw = img.convert("RGB").tobytes()
    counts: Counter[int] = Counter(raw)

    chi2_stat = 0.0
    dof = 0
    for k in range(128):
        c0 = counts.get(2 * k, 0)
        c1 = counts.get(2 * k + 1, 0)
        n = c0 + c1
        if n == 0:
            continue
        e = n / 2.0
        chi2_stat += (c0 - e) ** 2 / e + (c1 - e) ** 2 / e
        dof += 1

    score = chi2_stat / max(dof, 1)
    return score < LSB_STEG_THRESHOLD, score


def _re_encode(img: Image.Image, original_format: str) -> tuple[bytes, str]:
    """Re-encode *img* into a metadata-free byte stream.

    JPEG input → JPEG (quality=95, no subsampling, optimize).
    All others → PNG (lossless, universally supported, no metadata).
    RGBA and PA modes cannot be JPEG — fall through to PNG even for JPEG input.
    """
    buf = io.BytesIO()
    if original_format == "JPEG" and img.mode not in ("RGBA", "PA", "LA"):
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=95, subsampling=0, optimize=True)
        return buf.getvalue(), "JPEG"
    else:
        if img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
            img = img.convert("RGBA" if "A" in img.mode else "RGB")
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), "PNG"


def main() -> None:
    raw_bytes = sys.stdin.buffer.read()

    if not raw_bytes:
        json.dump(
            {
                "status": "REJECTED",
                "reject_reason": "empty_input",
                "format": None, "re_encoded_format": None,
                "width": None, "height": None, "mode": None,
                "steg_flag": False, "steg_score": None,
                "re_encoded_b64": None, "findings": [],
            },
            sys.stdout,
        )
        return

    findings: list[str] = []

    # --- Open image (lazy — only reads header at this point) ---
    try:
        img = Image.open(io.BytesIO(raw_bytes))
    except UnidentifiedImageError:
        json.dump(
            {
                "status": "REJECTED",
                "reject_reason": "unrecognised_image_format",
                "format": None, "re_encoded_format": None,
                "width": None, "height": None, "mode": None,
                "steg_flag": False, "steg_score": None,
                "re_encoded_b64": None, "findings": [],
            },
            sys.stdout,
        )
        return
    except Exception as exc:
        json.dump(
            {
                "status": "REJECTED",
                "reject_reason": f"open_error:{exc}",
                "format": None, "re_encoded_format": None,
                "width": None, "height": None, "mode": None,
                "steg_flag": False, "steg_score": None,
                "re_encoded_b64": None, "findings": [],
            },
            sys.stdout,
        )
        return

    original_format: str = img.format or "UNKNOWN"
    w, h = img.size

    # --- Dimension guard (header-only, no pixels loaded yet) ---
    if w > MAX_DIMENSION or h > MAX_DIMENSION:
        json.dump(
            {
                "status": "REJECTED",
                "reject_reason": f"image_dimension_exceeded:{w}x{h}",
                "format": original_format, "re_encoded_format": None,
                "width": w, "height": h, "mode": img.mode,
                "steg_flag": False, "steg_score": None,
                "re_encoded_b64": None, "findings": [],
            },
            sys.stdout,
        )
        return

    if w * h > MAX_PIXELS:
        json.dump(
            {
                "status": "REJECTED",
                "reject_reason": f"pixel_bomb:{w * h}",
                "format": original_format, "re_encoded_format": None,
                "width": w, "height": h, "mode": img.mode,
                "steg_flag": False, "steg_score": None,
                "re_encoded_b64": None, "findings": [],
            },
            sys.stdout,
        )
        return

    # --- Load pixels (deferred until after dimension check) ---
    try:
        img.load()
    except Exception as exc:
        json.dump(
            {
                "status": "REJECTED",
                "reject_reason": f"load_error:{exc}",
                "format": original_format, "re_encoded_format": None,
                "width": w, "height": h, "mode": img.mode,
                "steg_flag": False, "steg_score": None,
                "re_encoded_b64": None, "findings": [],
            },
            sys.stdout,
        )
        return

    # --- Multi-frame: note truncation, keep frame 0 ---
    try:
        n_frames = getattr(img, "n_frames", 1)
    except Exception:
        n_frames = 1
    if n_frames > 1:
        findings.append(f"multi_frame_truncated:frame_0_of_{n_frames}")
        img.seek(0)

    # --- EXIF orientation (must apply before metadata strip) ---
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass  # not all formats carry EXIF; failure is safe to ignore

    # --- Metadata strip via pixel-data round-trip ---
    try:
        stripped = Image.frombytes(img.mode, img.size, img.tobytes())
    except Exception as exc:
        json.dump(
            {
                "status": "REJECTED",
                "reject_reason": f"strip_error:{exc}",
                "format": original_format, "re_encoded_format": None,
                "width": w, "height": h, "mode": img.mode,
                "steg_flag": False, "steg_score": None,
                "re_encoded_b64": None, "findings": findings,
            },
            sys.stdout,
        )
        return

    # --- LSB chi-square steganography heuristic ---
    steg_flag = False
    steg_score: float | None = None
    if original_format in LOSSLESS_FORMATS:
        try:
            steg_flag, steg_score = _lsb_chi_square(stripped)
            if steg_flag:
                findings.append("lsb_steg_suspected")
        except Exception:
            pass  # heuristic failure is non-fatal

    # --- Re-encode (no metadata) ---
    try:
        re_encoded_bytes, re_encoded_format = _re_encode(stripped, original_format)
    except Exception as exc:
        json.dump(
            {
                "status": "REJECTED",
                "reject_reason": f"encode_error:{exc}",
                "format": original_format, "re_encoded_format": None,
                "width": w, "height": h, "mode": img.mode,
                "steg_flag": steg_flag, "steg_score": steg_score,
                "re_encoded_b64": None, "findings": findings,
            },
            sys.stdout,
        )
        return

    result: dict[str, Any] = {
        "status": "CLEAN",
        "reject_reason": None,
        "format": original_format,
        "re_encoded_format": re_encoded_format,
        "width": stripped.width,
        "height": stripped.height,
        "mode": stripped.mode,
        "steg_flag": steg_flag,
        "steg_score": steg_score,
        "re_encoded_b64": base64.b64encode(re_encoded_bytes).decode("ascii"),
        "findings": findings,
    }
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        json.dump(
            {
                "status": "REJECTED",
                "reject_reason": f"fatal:{exc}",
                "format": None, "re_encoded_format": None,
                "width": None, "height": None, "mode": None,
                "steg_flag": False, "steg_score": None,
                "re_encoded_b64": None, "findings": [],
            },
            sys.stdout,
        )
        sys.exit(1)
