"""
Shared pytest configuration.

Imports cfg from app.config (which loads backend/.env via load_dotenv + pydantic-settings)
and derives per-role DSNs by swapping credentials in the base DATABASE_URL.  All env vars
are set before any test module imports so that os.environ.get() calls in the modules see
the right values.
"""

import os
from urllib.parse import urlparse, urlunparse

from app.config import cfg  # triggers load_dotenv() + Settings instantiation


def _swap_creds(url: str, user: str, password: str) -> str:
    """Return url with the user/password component replaced."""
    p = urlparse(url)
    host = p.hostname + (f":{p.port}" if p.port else "")
    new_netloc = f"{user}:{password}@{host}"
    return urlunparse(p._replace(netloc=new_netloc))


# ── Derive the admin DSN (whatever DATABASE_URL resolves to) ─────────────────
_base_url = cfg.database_url or "postgresql://postgres:postgres@localhost:5432/secureclaim"
os.environ.setdefault("TEST_ADMIN_DSN", _base_url)

# ── Derive per-role DSNs ──────────────────────────────────────────────────────
_roles: dict[str, tuple[str, str]] = {
    "TEST_APP_DSN":                ("secureclaim_app",        "secureclaim_app"),
    "TEST_ORCHESTRATOR_DSN":       ("role_orchestrator",      "role_orchestrator"),
    "TEST_INTAKE_ACTOR_DSN":       ("role_intake_actor",      "role_intake_actor"),
    "TEST_IDENTITY_VERIFIER_DSN":  ("role_identity_verifier", "role_identity_verifier"),
    "TEST_CLAIMS_PROCESSOR_DSN":   ("role_claims_processor",  "role_claims_processor"),
    "TEST_SETTLEMENT_ACTOR_DSN":   ("role_settlement_actor",  "role_settlement_actor"),
}

for _env_key, (_user, _pw) in _roles.items():
    os.environ.setdefault(_env_key, _swap_creds(_base_url, _user, _pw))

# AUDIT_VERIFY_DSN uses the admin connection (full read access for chain verification)
os.environ.setdefault("AUDIT_VERIFY_DSN", _base_url)
