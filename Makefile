# Local Hub repro Makefile for telemetry-api

.PHONY: pull down up logs wait smoke repro deepclean seed-admin

pull:
	@echo "📥 Pulling Hub image..."
	@IMAGE_REPO=$${IMAGE_REPO:-shvin/telemetry-api} IMAGE_TAG=$${IMAGE_TAG:-v0.8.8-golden} docker compose -f docker-compose.yml -f compose.override.yml pull

down:
	@echo "🛑 Stopping and cleaning containers..."
	docker compose down -v --remove-orphans

up:
	@echo "🚀 Starting services..."
	set -a; [ -f .github/test.env ] && grep -v '^#' .github/test.env | xargs -I{} echo {}; set +a || true
	docker compose -f docker-compose.yml -f compose.override.yml up -d --no-build

logs:
	@echo "📋 Showing recent logs..."
	docker compose logs --no-color | tail -n 300

wait:
	@echo "⏳ Waiting for API to become healthy (timeout 60s)..."
	@for i in $$(seq 1 30); do \
		if python3 -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:80/v1/health').status == 200 else 1)" 2>/dev/null; then \
			echo "✅ API is healthy"; \
			exit 0; \
		fi; \
		echo "⏳ Waiting... ($$((i * 2))s)"; \
		sleep 2; \
	done; \
	echo "❌ API health check timeout"; \
	exit 1

smoke:
	@echo "🧪 Running smoke tests..."
	python3 scripts/smoke.py

repro: down pull up wait smoke logs

deepclean:
	@echo "🧹 Removing project images..."
	docker compose images -q | sort -u | xargs -r docker image rm -f

seed-admin:
	@docker exec -e TELEMETRY_SEED_KEYS="$${TELEMETRY_SEED_KEYS:-DEV_ADMIN_KEY_5a8f9ffdc3}" telemetry-api python -c "import app.db_boot as b; b.ensure_schema_and_seed_keys(); print('seeded')"

help:
	@echo "Available targets:"
	@echo "  repro      - Full repro: down, pull, up, wait, smoke, logs"
	@echo "  pull       - Pull Hub image"
	@echo "  up         - Start services (no build)"
	@echo "  down       - Stop and clean containers"
	@echo "  wait       - Wait for API health (60s timeout)"
	@echo "  smoke      - Run Python smoke tests"
	@echo "  logs       - Show recent logs"
	@echo "  deepclean  - Remove project images"
	@echo "  seed-admin - Seed admin keys in running container"
	@echo ""
	@echo "Usage examples:"
	@echo "  make repro                    # Default: shvin/telemetry-api:v0.8.8-golden"
	@echo "  make repro IMAGE_TAG=v0.8.6   # Specific tag"
	@echo "  make logs                     # View logs"
	@echo "  make down                     # Stop & clean"
