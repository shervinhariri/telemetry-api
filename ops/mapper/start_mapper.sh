#!/bin/bash
set -euo pipefail

# Start mapper with collector logs piped to stdin
echo "Starting NetFlow mapper..."

# Get collector logs and pipe to mapper
docker compose logs -f collector | grep "NETFLOW_V" | docker compose run --rm mapper python3 nf2ingest.py
