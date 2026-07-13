"""Central application configuration using pydantic-settings.

This is the sole place that loads .env on startup.  All other modules must
import cfg from here instead of calling load_dotenv() or os.environ.get()
directly.

pydantic-settings reads values in priority order:
  1. Real environment variables  (highest — always wins)
  2. backend/.env file           (via env_file below)
  3. Field defaults              (lowest)

load_dotenv() is also called here so that deeper system modules that still
read os.environ directly (e.g. agent_system, vault) see the values without
any extra setup.

Environment detection
---------------------
Render automatically injects RENDER=true into every deployed service.
Its absence signals a local dev environment.  Do NOT set RENDER manually.

Usage
-----
    from app.config import cfg

    cfg.environment        # "production" | "local"
    cfg.allowed_origins    # list[str] for CORSMiddleware
    cfg.database_url       # str
    cfg.is_cloud           # bool
"""
from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)

_ENV_FILE = Path(__file__).parent.parent / ".env"

# Populate os.environ from .env once so that any code using os.environ.get()
# directly (e.g. agent_system, vault) also sees the values.
load_dotenv(str(_ENV_FILE), override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Environment detection ─────────────────────────────────────────────────
    # Render sets RENDER=true automatically; treat its absence as local dev.
    render: str = Field(default="", alias="RENDER")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_cloud(self) -> bool:
        return self.render.lower() in ("true", "1", "yes")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def environment(self) -> str:
        return "production" if self.is_cloud else "local"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Production: set ALLOWED_ORIGINS on Render to your Vercel domain(s), comma-sep.
    # Local dev:  leave unset — defaults to "*" so no per-origin config is needed.
    allowed_origins_raw: str = Field(default="", alias="ALLOWED_ORIGINS")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_origins(self) -> list[str]:
        if self.allowed_origins_raw:
            return [o.strip() for o in self.allowed_origins_raw.split(",") if o.strip()]
        return [] if self.is_cloud else ["*"]

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(default="", alias="DATABASE_URL")

    # ── Qdrant (vector DB) ───────────────────────────────────────────────────
    qdrant_url: str = Field(default="", alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", alias="QDRANT_API_KEY")
    qdrant_policy_collection: str = Field(
        default="ProjectCitadel-policy_docs", alias="QDRANT_POLICY_COLLECTION"
    )
    qdrant_fraud_collection: str = Field(
        default="ProjectCitadel-fraud_rules", alias="QDRANT_FRAUD_COLLECTION"
    )
    qdrant_faq_collection: str = Field(
        default="ProjectCitadel-public_faq", alias="QDRANT_FAQ_COLLECTION"
    )

    # ── OpenTelemetry ─────────────────────────────────────────────────────────
    otel_endpoint: str = Field(
        default="http://localhost:4317", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_service_name: str = Field(
        default="secureclaim-backend", alias="OTEL_SERVICE_NAME"
    )

    # ── LLM providers ────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    google_model: str = Field(default="gemini-2.0-flash-lite", alias="GOOGLE_MODEL")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.1-8b-instant", alias="GROQ_MODEL")
    ollama_host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")
    ollama_model: str = Field(default="gemma4:12b", alias="OLLAMA_MODEL")

    # ── GitHub integration ────────────────────────────────────────────────────
    github_token: str = Field(default="", alias="GITHUB_TOKEN")
    github_repo: str = Field(default="", alias="GITHUB_REPO")

    # ── Adversarial agent ─────────────────────────────────────────────────────
    monthly_spend_cap_usd: float = Field(default=50.0, alias="MONTHLY_SPEND_CAP_USD")

    # ── Playground auth ───────────────────────────────────────────────────────
    playground_token: str = Field(default="citadel-demo-2026", alias="PLAYGROUND_TOKEN")

    # ── Startup log ───────────────────────────────────────────────────────────
    @model_validator(mode="after")
    def _log_startup(self) -> "Settings":
        if self.is_cloud and not self.allowed_origins:
            log.warning(
                "config: ALLOWED_ORIGINS is not set on Render — "
                "cross-origin requests will be blocked until you set it to your Vercel URL."
            )
        log.info(
            "config: environment=%s  cloud=%s  cors=%s",
            self.environment,
            self.is_cloud,
            self.allowed_origins,
        )
        return self


# Module-level singleton — import as `from app.config import cfg`.
cfg = Settings()
