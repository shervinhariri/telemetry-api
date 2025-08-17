#!/usr/bin/env bash
# docker_clean_reset.sh — Remove ALL docker state and rebuild project containers
set -euo pipefail

echo "==> Stopping compose and removing volumes"
docker compose down -v --remove-orphans || true

echo "==> Removing containers/images/volumes/networks (global)"
docker ps -aq | xargs -r docker rm -f
docker images -q | xargs -r docker rmi -f
docker volume ls -q | xargs -r docker volume rm
docker network ls --filter "type=custom" -q | xargs -r docker network rm

echo "==> System prune"
docker system prune -a --volumes -f

echo "==> Fresh build"
docker build -t telemetry-api:local .
docker run -d -p 80:8080 -e API_KEY=TEST_KEY -e REDACT_HEADERS=authorization,x-forwarded-for --name telemetry-api-test telemetry-api:local

echo "==> Done. Check logs:"
docker logs telemetry-api-test --tail=20
