"""
Shared pytest configuration.

Reads DATABASE_URL from backend/.env (manual parse — no extra dependency) and
derives per-role DSNs by swapping credentials in the base URL.  All env vars are
set before any test module imports so that os.environ.get() calls in the modules
see the right values.
"""

import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse


def _load_dotenv(env_path: Path) -> dict[str, str]:
    """Parse a .env file and return key→value pairs (comments and blanks skipped)."""
    result: dict[str, str] = {}
    if not env_path.exists():
        return result
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip optional surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        result[key] = value
    return result


def _swap_creds(url: str, user: str, password: str) -> str:
    """Return url with the user/password component replaced."""
    p = urlparse(url)
    host = p.hostname + (f":{p.port}" if p.port else "")
    new_netloc = f"{user}:{password}@{host}"
    return urlunparse(p._replace(netloc=new_netloc))


# ── Load .env relative to the backend root ───────────────────────────────────
_backend_root = Path(__file__).parent.parent
_env_vars = _load_dotenv(_backend_root / ".env")

# Populate os.environ only for keys not already set (real env always wins).
for _k, _v in _env_vars.items():
    os.environ.setdefault(_k, _v)

# ── Derive the admin DSN (whatever DATABASE_URL resolves to) ─────────────────
_base_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/secureclaim")
os.environ.setdefault("TEST_ADMIN_DSN", _base_url)

# ── Derive per-role DSNs ──────────────────────────────────────────────────────
_roles: dict[str, tuple[str, str]] = {
    "TEST_APP_DSN":                ("secureclaim_app",       "secureclaim_app"),
    "TEST_ORCHESTRATOR_DSN":       ("role_orchestrator",     "role_orchestrator"),
    "TEST_INTAKE_ACTOR_DSN":       ("role_intake_actor",     "role_intake_actor"),
    "TEST_IDENTITY_VERIFIER_DSN":  ("role_identity_verifier","role_identity_verifier"),
    "TEST_CLAIMS_PROCESSOR_DSN":   ("role_claims_processor", "role_claims_processor"),
    "TEST_SETTLEMENT_ACTOR_DSN":   ("role_settlement_actor", "role_settlement_actor"),
}

for _env_key, (_user, _pw) in _roles.items():
    os.environ.setdefault(_env_key, _swap_creds(_base_url, _user, _pw))

# AUDIT_VERIFY_DSN uses the admin connection (full read access for chain verification)
os.environ.setdefault("AUDIT_VERIFY_DSN", _base_url)
