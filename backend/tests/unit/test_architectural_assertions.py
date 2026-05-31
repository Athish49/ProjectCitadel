"""Architectural-assertion test suite (Sprint 5.1.8).

Static-analysis tests that guard hard-won design invariants. They run in
< 1 second with no network or DB. A failure means a structural coupling
constraint has been broken, not just a runtime bug.
"""
from __future__ import annotations

import ast
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).parent.parent.parent

pytestmark = pytest.mark.unit


# ── AST helpers ──────────────────────────────────────────────────────────────


def _imported_names(path: Path) -> set[str]:
    """Return every name bound by import statements in the file.

    'import anthropic' → {'anthropic'}
    'from agent_system.tools.registry import ToolRegistry' → {'ToolRegistry'}
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def _first_line_of_name(path: Path, name: str) -> int | None:
    """First source line containing a Name node with id==name."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == name:
            return node.lineno
    return None


def _first_line_of_attr(path: Path, attr: str) -> int | None:
    """First source line containing an Attribute node with attr==attr."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == attr:
            return node.lineno
    return None


def _first_line_inside_func(path: Path, func_name: str, name: str) -> int | None:
    """First line where Name(id==name) appears inside function func_name.

    Excludes module-level definitions so constants defined before the function
    don't shadow their first usage inside it.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            result: int | None = None
            for child in ast.walk(node):
                if isinstance(child, ast.Name) and child.id == name:
                    if result is None or child.lineno < result:
                        result = child.lineno
            return result
    return None


def _first_attr_inside_func(path: Path, func_name: str, attr: str) -> int | None:
    """First line where Attribute(attr==attr) appears inside function func_name."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            result: int | None = None
            for child in ast.walk(node):
                if isinstance(child, ast.Attribute) and child.attr == attr:
                    if result is None or child.lineno < result:
                        result = child.lineno
            return result
    return None


# ── module path constants ─────────────────────────────────────────────────────

_ORCHESTRATOR_MODULES = [
    "agent_system/orchestrator/state.py",
    "agent_system/orchestrator/transitions.py",
    "agent_system/orchestrator/budgets.py",
    "agent_system/orchestrator/intent_routing.py",
]

_ACTOR_MODULES = [
    "agent_system/actors/intake_actor.py",
    "agent_system/actors/identity_verifier_actor.py",
    "agent_system/actors/claims_processor_actor.py",
    "agent_system/actors/settlement_actor.py",
    "agent_system/actors/inquiry_actor.py",
]

_CUSTOMER_FACING_ACTORS = [
    "agent_system/actors/intake_actor.py",
    "agent_system/actors/settlement_actor.py",
    "agent_system/actors/inquiry_actor.py",
]


# ── test classes ──────────────────────────────────────────────────────────────


class TestOrchestratorIsNotLLM:
    """Orchestrator is a pure deterministic state machine — no LLM dependency."""

    @pytest.mark.parametrize("rel", _ORCHESTRATOR_MODULES)
    def test_no_anthropic_import(self, rel: str) -> None:
        names = _imported_names(BACKEND / rel)
        assert "anthropic" not in names, (
            f"{rel} must not import 'anthropic'. "
            "The orchestrator is a pure state machine; LLM calls belong in actors."
        )


class TestActorSecurityWiring:
    """Every LLM actor must be wired to both the Anthropic SDK and ToolRegistry."""

    @pytest.mark.parametrize("rel", _ACTOR_MODULES)
    def test_uses_anthropic(self, rel: str) -> None:
        names = _imported_names(BACKEND / rel)
        assert "anthropic" in names, (
            f"{rel} must import 'anthropic'. Actors drive LLM calls — missing import "
            "means the actor cannot make API calls."
        )

    @pytest.mark.parametrize("rel", _ACTOR_MODULES)
    def test_uses_tool_registry(self, rel: str) -> None:
        names = _imported_names(BACKEND / rel)
        assert "ToolRegistry" in names, (
            f"{rel} must import ToolRegistry. All tool invocations must go through "
            "the registry for capability-token enforcement and replay protection."
        )

    @pytest.mark.parametrize("rel", _CUSTOMER_FACING_ACTORS)
    def test_customer_facing_imports_egress_filter(self, rel: str) -> None:
        names = _imported_names(BACKEND / rel)
        assert "filter_output" in names, (
            f"{rel} is customer-facing and must import filter_output. "
            "Every customer-visible response must pass through the egress filter."
        )


class TestKnownAgentsRegistry:
    """KNOWN_AGENTS is the authoritative agent whitelist — additions require a security review."""

    def test_known_agents_exact_set(self) -> None:
        from agent_system.identity.keys import KNOWN_AGENTS

        expected = frozenset({
            "orchestrator",
            "intake_parser",
            "intake_actor",
            "identity_verifier",
            "document_parser",
            "claims_processor",
            "settlement_actor",
        })
        assert KNOWN_AGENTS == expected, (
            f"KNOWN_AGENTS has drifted. "
            f"Expected {sorted(expected)}, got {sorted(KNOWN_AGENTS)}. "
            "Adding an agent grants it key-signing authority — update this assertion "
            "only after a security review."
        )


class TestEgressAllowlist:
    """Expanding the URL allowlist widens the exfiltration surface."""

    def test_allowed_hosts_exact_set(self) -> None:
        from agent_system.egress.allowlist import ALLOWED_HOSTS

        expected = frozenset({
            "docs.secureclaim.example",
            "status.secureclaim.example",
        })
        assert ALLOWED_HOSTS == expected, (
            f"ALLOWED_HOSTS has changed. "
            f"Expected {sorted(expected)}, got {sorted(ALLOWED_HOSTS)}. "
            "Adding a host allows the LLM to exfiltrate data to it — "
            "get a security review before expanding the allowlist."
        )


class TestStateMachineTopology:
    """All valid claim-workflow edges must advance strictly forward through topological rank."""

    _RANK: dict[str, int] = {
        "INTAKE": 0,
        "IDENTITY_PENDING": 1,
        "IDENTITY_VERIFIED": 2,
        "PROCESSING": 3,
        "DECIDED": 4,
        "SETTLED": 5,
        "ESCALATED": 5,
        "DENIED": 5,
        "CLOSED": 6,
    }

    def test_all_edges_are_forward(self) -> None:
        from agent_system.orchestrator.transitions import _VALID_EDGES

        for src, dst in _VALID_EDGES:
            src_rank = self._RANK[src.value]
            dst_rank = self._RANK[dst.value]
            assert src_rank < dst_rank, (
                f"Backward or lateral edge: {src.value}→{dst.value} "
                f"(rank {src_rank}→{dst_rank}). "
                "The state machine must only advance — backward edges enable replay attacks."
            )

    def test_terminal_stage_has_no_outbound_edges(self) -> None:
        from agent_system.orchestrator.transitions import TERMINAL_STAGE, _VALID_EDGES

        outbound = [(s.value, d.value) for s, d in _VALID_EDGES if s == TERMINAL_STAGE]
        assert outbound == [], (
            f"Terminal stage {TERMINAL_STAGE.value} has outbound edges: {outbound}. "
            "A closed claim must not be re-opened."
        )


class TestRLSCoverage:
    """Migration must enable RLS on every customer-scoped table.

    If you add a new customer-scoped table, you must:
      1. ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
      2. ALTER TABLE <table> FORCE ROW LEVEL SECURITY;
      3. Add the table name to _EXPECTED_RLS_TABLES below.
    """

    _MIGRATION = BACKEND / "db" / "migrations" / "001_initial_schema.sql"
    _RLS_PATTERN = re.compile(
        r"ALTER TABLE (\w+) ENABLE ROW LEVEL SECURITY", re.IGNORECASE
    )
    _EXPECTED_RLS_TABLES = frozenset({
        "customers",
        "policies",
        "vehicles",
        "claims",
        "evidence",
        "settlements",
        "complaints",
    })
    # These tables are protected by GRANT revocation, not row-level policies.
    _GRANT_ONLY_TABLES = frozenset({"pii_vault", "fraud_scores"})

    def _rls_tables(self) -> frozenset[str]:
        sql = self._MIGRATION.read_text(encoding="utf-8")
        return frozenset(m.group(1) for m in self._RLS_PATTERN.finditer(sql))

    def test_rls_enabled_on_all_customer_tables(self) -> None:
        rls_tables = self._rls_tables()
        assert rls_tables == self._EXPECTED_RLS_TABLES, (
            f"RLS table mismatch. "
            f"Got {sorted(rls_tables)}, want {sorted(self._EXPECTED_RLS_TABLES)}. "
            "If you added a new customer-scoped table, enable RLS AND update this assertion."
        )

    def test_grant_only_tables_have_no_rls_policies(self) -> None:
        rls_tables = self._rls_tables()
        overlap = self._GRANT_ONLY_TABLES & rls_tables
        assert not overlap, (
            f"Tables {sorted(overlap)} are grant-protected and must NOT have RLS enabled. "
            "They rely solely on GRANT revocation — adding RLS policies would be misleading."
        )


class TestCanonicalPayloadCoverage:
    """_canonical_payload() must cover every CapabilityToken field except 'signature'.

    A field missing from the payload means a tampered value goes undetected;
    'signature' appearing in the payload creates a circular dependency.
    """

    def test_all_non_signature_fields_in_payload(self) -> None:
        from agent_system.tools.capability_tokens import CapabilityToken, _canonical_payload

        all_fields = set(CapabilityToken.model_fields.keys())
        required_fields = all_fields - {"signature"}

        token = CapabilityToken(
            token_id=uuid.uuid4(),
            issued_by="orchestrator",
            agent_id="intake_actor",
            tool="submit_claim",
            scope={"claim_id": "test-123"},
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            signature="ab" * 32,
        )
        payload_dict = json.loads(_canonical_payload(token).decode())

        for field_name in required_fields:
            assert field_name in payload_dict, (
                f"Field '{field_name}' is in CapabilityToken but absent from "
                "_canonical_payload(). A tampered '{field_name}' would pass signature "
                "verification undetected."
            )

        assert "signature" not in payload_dict, (
            "'signature' must NOT appear in _canonical_payload() — "
            "it would create a circular dependency in the signing/verification path."
        )


class TestEgressFilterStepOrder:
    """The four egress filter steps must execute in the documented order.

    Order matters for security:
      1. SECRET kill-switch — must short-circuit before any processing
      2. URL strip — must run on full text before PII check (URLs may contain PII)
      3. PII check — must run on URL-stripped text before truncation
      4. Length cap — last step only; truncating first would hide PII in the tail
    """

    _FILTER_PY = BACKEND / "agent_system" / "egress" / "filter.py"

    def test_secret_check_before_url_strip(self) -> None:
        secret_line = _first_attr_inside_func(self._FILTER_PY, "filter_output", "SECRET")
        url_line = _first_line_inside_func(self._FILTER_PY, "filter_output", "strip_urls")
        assert secret_line is not None, "DataLabel.SECRET not found in filter_output()"
        assert url_line is not None, "strip_urls() call not found in filter_output()"
        assert secret_line < url_line, (
            f"Step 1 (SECRET check, line {secret_line}) must precede "
            f"Step 2 (URL strip, line {url_line})."
        )

    def test_url_strip_before_pii_check(self) -> None:
        url_line = _first_line_inside_func(self._FILTER_PY, "filter_output", "strip_urls")
        pii_line = _first_line_inside_func(self._FILTER_PY, "filter_output", "find_pii")
        assert url_line is not None, "strip_urls() call not found in filter_output()"
        assert pii_line is not None, "find_pii() call not found in filter_output()"
        assert url_line < pii_line, (
            f"Step 2 (URL strip, line {url_line}) must precede "
            f"Step 3 (PII check, line {pii_line})."
        )

    def test_pii_check_before_truncation(self) -> None:
        pii_line = _first_line_inside_func(self._FILTER_PY, "filter_output", "find_pii")
        trunc_line = _first_line_inside_func(self._FILTER_PY, "filter_output", "MAX_OUTPUT_CHARS")
        assert pii_line is not None, "find_pii() call not found in filter_output()"
        assert trunc_line is not None, "MAX_OUTPUT_CHARS not found in filter_output()"
        assert pii_line < trunc_line, (
            f"Step 3 (PII check, line {pii_line}) must precede "
            f"Step 4 (truncation, line {trunc_line}). "
            "Truncating first would hide PII in the discarded tail."
        )
