.PHONY: up down logs ps clean health migrate seed test-rls test-agent-roles test-audit-chain test-primitives verify-chain run trace-smoke build-pdf-sandbox test-pdf-sandbox build-image-sandbox test-image-sandbox test-vision-redaction test-pdf-hidden

up:
	docker compose up -d --wait
	@$(MAKE) health

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

clean:
	docker compose down -v

health:
	@echo "==> Checking service endpoints from host"
	@FAIL=0; \
	printf "postgres   : "; docker compose exec -T postgres pg_isready -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-secureclaim} > /dev/null 2>&1 && echo OK || { echo FAIL; FAIL=1; }; \
	printf "chromadb   : "; curl -fsS http://localhost:$${CHROMADB_PORT:-8000}/api/v2/heartbeat > /dev/null 2>&1 && echo OK || { echo FAIL; FAIL=1; }; \
	printf "tempo      : "; curl -fsS http://localhost:$${TEMPO_HTTP_PORT:-3200}/ready > /dev/null 2>&1 && echo OK || { echo FAIL; FAIL=1; }; \
	printf "otel-coll  : "; curl -fsS http://localhost:$${OTEL_HEALTH_PORT:-13133}/ > /dev/null 2>&1 && echo OK || { echo FAIL; FAIL=1; }; \
	printf "grafana    : "; curl -fsS http://localhost:$${GRAFANA_PORT:-3001}/api/health > /dev/null 2>&1 && echo OK || { echo FAIL; FAIL=1; }; \
	exit $$FAIL

migrate:
	uv run python -m db.migrate

seed:
	uv run python -m db.seed

test-rls:
	uv run pytest tests/integration/test_rls.py -v -m integration

test-agent-roles:
	uv run pytest tests/integration/test_agent_roles.py -v -m integration

test-audit-chain:
	uv run pytest tests/unit/test_audit_chain.py -v -m unit
	uv run pytest tests/integration/test_audit_chain.py -v -m integration

verify-chain:
	uv run python -m audit.verify

run:
	uv run uvicorn app.main:app --port $${FASTAPI_PORT:-8080} --reload

# Hit /health then poll Tempo until the trace appears (accounts for 10 s idle period).
trace-smoke:
	@echo "==> Sending request to /health"
	curl -fsS http://localhost:$${FASTAPI_PORT:-8080}/health
	@echo ""
	@echo "==> Waiting 15 s for Tempo idle period..."
	@sleep 15
	@echo "==> Querying Tempo for secureclaim-backend traces"
	@curl -fsS "http://localhost:$${TEMPO_HTTP_PORT:-3200}/api/search?service.name=secureclaim-backend&limit=3" | python3 -m json.tool

build-pdf-sandbox:
	docker build -t secureclaim-pdf-sandbox:latest sandbox/pdf/

test-pdf-sandbox:
	uv run pytest tests/unit/test_pdf_sandbox.py -v -m unit
	uv run pytest tests/integration/test_pdf_sandbox.py -v -m integration

build-image-sandbox:
	docker build -t secureclaim-image-sandbox:latest sandbox/image/

test-image-sandbox:
	uv run pytest tests/unit/test_image_sandbox.py -v -m unit
	uv run pytest tests/integration/test_image_sandbox.py -v -m integration

test-vision-redaction:
	uv run pytest tests/unit/test_vision_redaction.py -v -m unit
	uv run pytest tests/integration/test_vision_redaction.py -v -m integration

test-pdf-hidden:
	uv run pytest tests/unit/test_pdf_hidden.py -v -m unit
	uv run pytest tests/integration/test_pdf_hidden.py -v -m integration

# Phase 1 milestone: all primitives tests passing (grows as sprints complete)
test-primitives: test-rls test-agent-roles test-audit-chain
