.PHONY: up down logs ps clean health migrate seed test-rls test-agent-roles test-audit-chain test-primitives verify-chain run trace-smoke build-pdf-sandbox test-pdf-sandbox build-image-sandbox test-image-sandbox test-vision-redaction test-pdf-hidden test-orchestrator test-prompt-registry test-parser-schemas test-intake-parser test-intake-actor test-identity-verifier-actor test-claims-processor-actor test-settlement-actor test-vertical-slice test-signed-envelopes test-capability-token-pipeline test-attack-suite test-classify-damage

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

test-orchestrator:
	uv run pytest tests/unit/test_orchestrator.py -v -m unit

test-prompt-registry:
	uv run pytest tests/unit/test_prompt_registry.py -v -m unit

test-parser-schemas:
	uv run pytest tests/unit/test_parser_schemas.py -v -m unit

test-intake-parser:
	uv run pytest tests/unit/test_intake_parser.py -v -m unit

test-intake-actor:
	uv run pytest tests/unit/test_intake_actor.py -v -m unit

test-identity-verifier-actor:
	uv run pytest tests/unit/test_identity_verifier_actor.py -v -m unit

test-claims-processor-actor:
	uv run pytest tests/unit/test_claims_processor_actor.py -v -m unit

test-settlement-actor:
	uv run pytest tests/unit/test_settlement_actor.py -v -m unit

test-vertical-slice:
	uv run pytest tests/integration/test_vertical_slice_e2e.py -v -m integration

test-signed-envelopes:
	uv run pytest tests/unit/test_signed_envelopes.py -v -m unit

test-capability-token-pipeline:
	uv run pytest tests/integration/test_capability_token_pipeline.py -v -m integration

test-attack-suite:
	uv run pytest tests/unit/test_attack_suite.py -v -m unit

test-classify-damage:
	uv run pytest tests/unit/test_classify_damage.py -v -m unit

# Phase 1 milestone: all primitives tests passing (grows as sprints complete)
test-primitives: test-rls test-agent-roles test-audit-chain
