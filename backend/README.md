# SecureClaim AI — Backend

Resilient multi-agent claims system. Specs live in `../development_docs/`.

## Quickstart

```bash
cp .env.example .env
make up      # boots postgres + chromadb + otel-collector + tempo + grafana
make ps      # show container status
make health  # poll each service's health endpoint from host
make logs    # follow container logs
make down    # stop containers (volumes preserved)
make clean   # stop containers AND remove volumes (destructive)
```

After `make up`, Grafana is reachable at <http://localhost:3001> with the Tempo
datasource pre-provisioned (anonymous admin enabled for local dev). Port 3001
(not the conventional 3000) leaves 3000 free for the forthcoming `frontend/`
Next.js dev server.

## Layout

See `development_docs/02_Technical_Architecture.md` §6.2 for the canonical tree.
Console/frontend code lives in the sibling `frontend/` repo (forthcoming).

## Phase 1 status

Sprint 1.1 task 1.1.1 — Docker Compose skeleton. `make up` boots the stack.
