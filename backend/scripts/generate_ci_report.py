#!/usr/bin/env python3
"""
Generate console/public/ci-test-results.json from pytest-json-report artifacts.

Called by the GitHub Actions red-team workflow after both test jobs complete.
Runs from the repo root.

Reads (env-configurable):
  $UNIT_RESULTS        (default: artifacts/unit-results.json)
  $INTEGRATION_RESULTS (default: artifacts/integration-results.json, optional)

Writes:
  console/public/ci-test-results.json
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Attack ID coverage: maps test file stem → list of attack IDs exercised ────
FILE_ATTACK_MAP: dict[str, list[int]] = {
    "test_attack_suite":                    [1, 2, 3, 4, 5, 6, 7, 9, 20, 21, 25, 29, 37],
    "test_sanitisation":                    [1, 5],
    "test_intake_parser":                   [1, 2],
    "test_pdf_sandbox":                     [2, 6],
    "test_pdf_hidden":                      [2, 6],
    "test_image_sandbox":                   [6],
    "test_vision_redaction":                [6],
    "test_ed25519_signing":                 [4],
    "test_signed_envelopes":                [4, 8],
    "test_capability_tokens":               [4, 29],
    "test_capability_token_bypass_probes":  [4, 29],
    "test_capability_token_pipeline":       [4, 29],
    "test_tool_registry":                   [4, 29],
    "test_egress_filter":                   [20, 25],
    "test_egress_probes":                   [20, 25],
    "test_rls":                             [20, 28, 37],
    "test_cross_customer_probes":           [20, 28, 37],
    "test_agent_roles":                     [20, 28, 37],
    "test_pii_vault":                       [20],
}


def _load(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[warn] could not parse {path}: {exc}", file=sys.stderr)
        return None


def _suite_stats(report: dict | None) -> dict | None:
    if report is None:
        return None
    summary = report.get("summary", {})
    return {
        "total":            summary.get("total", 0),
        "passed":           summary.get("passed", 0),
        "failed":           summary.get("failed", 0) + summary.get("error", 0),
        "duration_seconds": round(report.get("duration", 0.0), 2),
    }


def _attack_coverage(reports: list[dict]) -> dict[str, dict]:
    """Tally pass/fail per attack ID by walking test node IDs."""
    coverage: dict[int, dict] = {}

    for report in reports:
        for test in report.get("tests", []):
            nodeid: str = test.get("nodeid", "")
            # nodeid shape: "tests/unit/test_foo.py::Class::method"
            parts = nodeid.split("::")
            if not parts:
                continue
            file_stem = Path(parts[0]).stem
            attack_ids = FILE_ATTACK_MAP.get(file_stem, [])
            if not attack_ids:
                continue

            passed = test.get("outcome") == "passed"
            for aid in attack_ids:
                if aid not in coverage:
                    coverage[aid] = {"tests": 0, "passed": 0, "failed": 0}
                coverage[aid]["tests"] += 1
                if passed:
                    coverage[aid]["passed"] += 1
                else:
                    coverage[aid]["failed"] += 1

    return {str(k): v for k, v in sorted(coverage.items())}


def main() -> None:
    repo_root = Path(__file__).parent.parent.parent  # backend/scripts/ → repo root

    unit_path = Path(os.environ.get("UNIT_RESULTS", "artifacts/unit-results.json"))
    int_path  = Path(os.environ.get("INTEGRATION_RESULTS", "artifacts/integration-results.json"))

    unit_report = _load(unit_path)
    int_report  = _load(int_path)

    if unit_report is None:
        print(f"[error] unit results not found at {unit_path}", file=sys.stderr)
        sys.exit(1)

    unit_stats = _suite_stats(unit_report)
    int_stats  = _suite_stats(int_report)

    valid_reports = [r for r in [unit_report, int_report] if r is not None]
    attack_coverage = _attack_coverage(valid_reports)

    sha = os.environ.get("GITHUB_SHA", "")
    result = {
        "timestamp":       datetime.now(tz=timezone.utc).isoformat(),
        "commit":          sha,
        "commit_short":    sha[:7] if sha else "",
        "branch":          os.environ.get("GITHUB_REF_NAME", ""),
        "run_url":         os.environ.get("GITHUB_RUN_URL", ""),
        "unit":            unit_stats,
        "integration":     int_stats,
        "attack_coverage": attack_coverage,
    }

    out_path = repo_root / "console" / "public" / "ci-test-results.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[ok] wrote {out_path}")

    # Exit non-zero if any tests failed (so the publish job shows red)
    total_failed = (unit_stats["failed"] if unit_stats else 0) + \
                   (int_stats["failed"]  if int_stats  else 0)
    if total_failed:
        print(f"[warn] {total_failed} tests failed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
