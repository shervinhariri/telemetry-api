#!/bin/bash
set -euo pipefail

# Ingest Test Script for Telemetry API

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo "❌ .env file not found"
    exit 1
fi

echo "📥 Testing API ingest at https://$DOMAIN/v1/ingest"

# Check if sample data exists
if [ ! -f "samples/zeek_conn.json" ]; then
    echo "❌ Sample data not found: samples/zeek_conn.json"
    exit 1
fi

# Test ingest endpoint
echo "📊 Sending test data..."
response=$(curl -s -X POST "https://$DOMAIN/v1/ingest" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    --data @samples/zeek_conn.json 2>/dev/null || echo "FAILED")

if [ "$response" = "FAILED" ]; then
    echo "❌ Ingest test failed"
    echo "   Make sure:"
    echo "   1. API_KEY is correct in .env"
    echo "   2. Services are running: docker compose ps"
    echo "   3. Check logs: ./scripts/logs.sh"
    exit 1
fi

echo "✅ Ingest test passed"
echo "📊 Response:"
echo "$response" | jq .
