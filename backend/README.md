# SecureClaim AI — Backend

Resilient multi-agent claims pipeline. Specs live in `../development_docs/`. The Console (Next.js) lives in `../console/`.

## Quick start

```bash
cp .env.example .env          # set ANTHROPIC_API_KEY and DATABASE_URL
make up                       # postgres + otel-collector + tempo + grafana
make migrate                  # schema migrations + RLS policies
make seed                     # 30 claims, customers, policies, vehicles
make health                   # verify all services ready
```

Run the API:

```bash
uv run uvicorn app.main:app --reload --port 8080
```

Services after `make up`:

| Service | URL |
|---------|-----|
| API | http://localhost:8080 |
| PostgreSQL | localhost:5432 |
| Grafana | http://localhost:3001 |
| Tempo | http://localhost:3200 |
| Qdrant | cloud (see QDRANT_URL in .env) |

## Tests

```bash
# Unit tests (no docker required)
uv run pytest tests/unit/ -m unit -v

# Integration tests (requires make up + make migrate)
uv run pytest tests/integration/ -m integration -v

# Targeted probe suites
make test-cross-customer-probes
make test-egress-probes
make test-cap-token-bypass-probes
make test-arch-assertions

# Formal spec
make formal-check          # 30 invariant tests (pure Python BFS)
make formal-conformance    # 102 conformance tests
```

## Adversarial agent

```bash
# Runs in a Docker-isolated network; can reach the API but not Postgres directly.
docker compose --profile adversarial up -d --build
# Monthly spend capped at $50 (MONTHLY_SPEND_CAP_USD in .env)
```

## Layout

```
backend/
├── adversarial_agent/      # Red-team agent container
├── agent_system/
│   ├── actors/             # intake, identity, claims_processor, settlement
│   ├── orchestrator/       # state machine + transitions (no LLM)
│   ├── parser/             # intake parser (P1 dual-LLM)
│   └── tools/              # tool implementations + capability token gate
├── audit/                  # hash-chain log + verifier (P9)
├── app/                    # FastAPI app + showcase routes + SSE
├── data/
│   └── attack_payloads/    # 32 PDFs, 23 images, 159 text variants
├── db/                     # migrations, seed, RLS policies (P7)
├── formal/                 # TLA+ spec + Python BFS checker
├── sandbox/                # PDF + image processing sandboxes (P5, P6)
├── scripts/                # CI report generator
└── tests/
    ├── unit/               # 48 files, ≥1 189 tests
    └── integration/        # 17 files, requires live DB
```

See `../development_docs/` for the full architecture and threat model.
