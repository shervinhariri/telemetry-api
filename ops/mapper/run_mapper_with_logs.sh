#!/bin/bash
set -euo pipefail

echo "Starting NetFlow mapper with collector logs..."

# Run mapper in background and pipe collector logs to it
docker compose logs -f collector | grep "NETFLOW_V" | docker compose run --rm mapper python3 nf2ingest.py &
MAPPER_PID=$!

echo "Mapper started with PID: $MAPPER_PID"

# Wait for mapper to finish
wait $MAPPER_PID
