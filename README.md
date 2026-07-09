# SecureClaim AI — Resilient Agentic AI

A multi-agent insurance-claims pipeline engineered against a 79-category attack taxonomy. Built as a security-engineering portfolio piece: the insurance domain is a vehicle, not the subject.

**What this demonstrates:** how to build a multi-agent AI system where security properties are structural rather than bolt-on — RLS enforced in the database, capability tokens cryptographically signed, information flow enforced by the type system, audit integrity guaranteed by hash-chaining.

---

## Numbers

| Dimension | Count |
|-----------|-------|
| Defense patterns implemented | 12 (P1–P12) |
| Attack categories in taxonomy | 79 |
| LIVE attacks (empirically tested) | 39 |
| Unit tests | ≥1 189 |
| Integration tests | 17 files |
| Formal spec invariants (Python BFS) | 30 |
| Formal conformance tests | 102 |
| Residual risks documented | 13 |

---

## Architecture

Four named agents; deterministic orchestrator; no LLM in the control plane.

```
Untrusted input
       │
       ▼
┌─────────────┐  JSON schema   ┌────────────────────┐
│ Intake      │ ─────────────► │ Identity Verifier  │
│ Actor       │  (P1 dual-LLM) │ Actor              │
└─────────────┘                └─────────┬──────────┘
                                         │ signed capability token (P8)
                                         ▼
                              ┌────────────────────┐
                              │ Claims Processor   │  ← IFC labels (P3)
                              │ Actor              │  ← RLS (P7)
                              └─────────┬──────────┘  ← egress filter (P10)
                                        │
                                        ▼
                              ┌────────────────────┐
                              │ Settlement Actor   │
                              └─────────┬──────────┘
                                        │
                                        ▼
                              hash-chained audit row (P9)
```

**Orchestrator** is a pure state machine (`advance_stage()`). It never calls an LLM. Every agent transition requires a guard predicate to pass.

**Defense patterns (P1–P12):**

| ID | Pattern | What it prevents |
|----|---------|-----------------|
| P1 | Dual-LLM (parser + actor) | Prompt injection reaching business logic |
| P2 | Deterministic orchestrator | LLM hijacking control flow |
| P3 | IFC information-flow labels | Cross-classification data leakage |
| P4 | Capability tokens (Ed25519) | Unauthorised tool invocation |
| P5 | Sandboxed tool execution | Malicious tool output escaping |
| P6 | Vision pre-redaction | PII in images reaching the LLM |
| P7 | PostgreSQL RLS | Cross-customer data access |
| P8 | Per-agent asymmetric identity | Agent impersonation |
| P9 | Hash-chained audit log | Tamper-evident event trail |
| P10 | Egress filter (PII + URL) | Data exfiltration via LLM output |
| P11 | Token + cost budgets | Denial-of-wallet / runaway spend |
| P12 | Signed prompt registry | System-prompt tampering |

---

## Repository layout

```
ProjectCitadel/
├── backend/                    # Python 3.13 · FastAPI · uv
│   ├── agent_system/           # 4 actors + orchestrator + tools
│   ├── adversarial_agent/      # Red-team agent (Docker-isolated)
│   ├── audit/                  # Hash-chain implementation + verifier
│   ├── app/                    # FastAPI application
│   ├── db/                     # Migrations, seed, RLS policies
│   ├── formal/                 # TLA+ spec + Python BFS checker
│   ├── sandbox/                # PDF and image processing sandboxes
│   ├── tests/
│   │   ├── unit/               # 48 files, ≥1 189 tests
│   │   └── integration/        # 17 files, requires make up + make migrate
│   ├── docker-compose.yml
│   └── Makefile
├── console/                    # Next.js 15 · Tailwind v4 · TypeScript
│   ├── app/                    # App Router pages
│   ├── components/             # UI components
│   └── lib/                    # Data, hooks, types
├── development_docs/           # 6 internal specs (Doc 01–06)
├── RESIDUAL_RISKS.md           # 13 named residual risks
├── SECURITY.md                 # Vulnerability disclosure policy
└── CONTRIBUTING.md
```

---

## Quick start

### Backend

**Prerequisites:** Docker, [uv](https://github.com/astral-sh/uv), Python 3.13

```bash
cd backend
cp .env.example .env          # fill in ANTHROPIC_API_KEY
make up                       # postgres + qdrant + otel-collector + tempo + grafana
make migrate                  # apply schema migrations + RLS policies
make seed                     # load 30 claims, customers, policies
make health                   # verify all services ready
```

Run the API:

```bash
uv run uvicorn app.main:app --reload --port 8080
```

### Console

**Prerequisites:** Node.js 20+

```bash
cd console
npm install
npm run dev                   # http://localhost:3000
```

### Run the tests

```bash
# Unit tests only (no docker required)
cd backend && uv run pytest tests/unit/ -m unit

# Full suite (requires make up + make migrate)
uv run pytest tests/unit/ tests/integration/

# Formal spec check
make formal-check             # 30 invariant tests
make formal-conformance       # 102 conformance tests

# Targeted probes
make test-cross-customer-probes
make test-egress-probes
make test-cap-token-bypass-probes
make test-arch-assertions
```

### Adversarial agent

```bash
docker compose --profile adversarial up -d --build
# Attacker runs in an isolated network; can reach the API but not Postgres directly.
# Monthly spend capped at $50 USD (configurable via MONTHLY_SPEND_CAP_USD).
```

---

## Formal specification

The workflow state machine is specified in TLA+ (`backend/formal/workflow.tla`) and verified by an exhaustive Python BFS model-checker (`backend/formal/check_spec.py`).

**Verified invariants:**
- `TypeOK` — all variables remain in their declared domains
- `ClosedIsAbsorbing` — no transition out of `CLOSED`
- `ForwardProgress` — every transition increases topological rank
- `EventualClosure` — under weak fairness, every reachable state reaches `CLOSED`

The implementation's 11 transition edges and guard semantics are proven to match the spec exactly in `tests/unit/test_formal_conformance.py`.

---

## Residual risks

Thirteen residual risks are documented in [`RESIDUAL_RISKS.md`](RESIDUAL_RISKS.md) and rendered at `/residual` in the Console. Each entry names the exposure, explains why it was not fully eliminated, and describes the production mitigation in place.

Status summary: 9 accepted · 2 planned · 1 won't-do · 1 accepted (training-data scope).

---

## Documentation

Six internal specs live in [`development_docs/`](development_docs/) and are served as rendered web pages at `/docs` in the Console.

| Doc | Contents |
|-----|----------|
| [01 PRD](development_docs/01_PRD_Product_Requirements.md) | Product requirements, user stories, acceptance criteria |
| [02 TAD](development_docs/02_Technical_Architecture.md) | Architecture, defense patterns, agent design |
| [03 Data Model](development_docs/03_Data_Model_Schema.md) | Schema, RLS policies, data classification |
| [04 Threat Model](development_docs/04_Security_Threat_Model.md) | 79-category attack taxonomy, residual risks |
| [05 Roadmap](development_docs/05_Implementation_Roadmap.md) | Sprint-by-sprint implementation plan |
| [06 Console Spec](development_docs/06_Showcase_Platform_Spec.md) | Console design system, pages, interactions |

---

## Stack

**Backend:** Python 3.13 · FastAPI · PostgreSQL 16 · Qdrant · OpenTelemetry · Grafana Tempo · Docker Compose · uv · Anthropic Claude API

**Console:** Next.js 15 (App Router, RSC) · TypeScript · Tailwind v4 · Framer Motion · React Flow · Shiki · react-markdown

**Security:** Ed25519 (PyCA cryptography) · PostgreSQL RLS · SHA-256 hash chain · seccomp-bpf (tool sandbox)

**Formal:** TLA+ · Python BFS model-checker · pytest (unit + integration)

---

## Licence

MIT. See [LICENSE](LICENSE) if present; otherwise treat as MIT until a LICENSE file is added.

---

*Engineered by [Athish G R](https://github.com/Athish49). PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Security issues — see [SECURITY.md](SECURITY.md).*
