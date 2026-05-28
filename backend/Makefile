.PHONY: up down logs ps clean health

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
