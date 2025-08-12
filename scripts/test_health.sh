#!/bin/bash
set -euo pipefail

# Health Test Script for Telemetry API

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo "❌ .env file not found"
    exit 1
fi

echo "🏥 Testing API health at https://$DOMAIN/v1/health"

# Test API health endpoint
response=$(curl -fsSL "https://$DOMAIN/v1/health" 2>/dev/null || echo "FAILED")

if [ "$response" = "FAILED" ]; then
    echo "❌ Health check failed"
    echo "   Make sure:"
    echo "   1. Domain $DOMAIN points to this server"
    echo "   2. Services are running: docker compose ps"
    echo "   3. Check logs: ./scripts/logs.sh"
    exit 1
fi

echo "✅ Health check passed"
echo "📊 Response: $response"
