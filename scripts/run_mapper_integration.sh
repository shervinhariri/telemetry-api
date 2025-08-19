#!/bin/bash
set -euo pipefail

echo "🧪 Starting NetFlow Mapper Integration Test"
echo "============================================"

# Check if services are running
if ! docker compose ps api | grep -q "Up"; then
    echo "❌ API service is not running. Start it with:"
    echo "   docker compose up -d api"
    exit 1
fi

if ! docker compose ps collector | grep -q "Up"; then
    echo "❌ Collector service is not running. Start it with:"
    echo "   docker compose up -d collector"
    exit 1
fi

echo "✅ Services are running"
echo ""

# Start mapper in background with collector logs piped to it
echo "🚀 Starting mapper with collector logs..."
docker compose logs -f collector | grep "NETFLOW_V" | sed 's/.*| //' | docker compose run --rm mapper python3 nf2ingest.py &
MAPPER_PID=$!

echo "📊 Mapper started with PID: $MAPPER_PID"
echo ""

# Wait a moment for mapper to start
sleep 2

# Generate test data
echo "📡 Generating test NetFlow data..."
python3 scripts/generate_test_netflow.py --count 10 --flows 3

echo ""
echo "⏳ Waiting for processing..."
sleep 5

# Check API metrics
echo "📈 Checking API metrics..."
curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/metrics?window=300" | jq '.requests_total, .records_processed, .eps'

echo ""
echo "🔍 Checking mapper logs..."
docker compose logs mapper 2>/dev/null | tail -10 || echo "No mapper logs found"

echo ""
echo "✅ Integration test completed!"
echo "   To stop the mapper, run: kill $MAPPER_PID"
echo "   To monitor mapper logs: docker compose logs -f mapper"
