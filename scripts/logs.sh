#!/bin/bash
set -euo pipefail

# Logs Script for Telemetry API

echo "📋 Viewing service logs..."
echo "Press Ctrl+C to exit"
echo ""

# Follow logs from both services
docker compose logs -f api caddy
