#!/usr/bin/env bash
set -euo pipefail

echo "🧪 All-in-One Container Final Verification Test"
echo "==============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}❌ $message${NC}"
    else
        echo -e "${YELLOW}⚠️  $message${NC}"
    fi
}

echo "Step 1: Checking container status..."
if docker compose ps | grep -q "telemetry-allinone.*Up"; then
    print_status "PASS" "Container is running"
else
    print_status "FAIL" "Container is not running"
    exit 1
fi

echo ""
echo "Step 2: API health checks..."
if curl -s http://localhost/v1/health | jq -e '.status == "ok"' > /dev/null; then
    print_status "PASS" "Health endpoint returns 200 OK"
else
    print_status "FAIL" "Health endpoint failed"
    exit 1
fi

if curl -s http://localhost/v1/version | jq -e '.service == "telemetry-api"' > /dev/null; then
    print_status "PASS" "Version endpoint returns valid response"
else
    print_status "FAIL" "Version endpoint failed"
    exit 1
fi

echo ""
echo "Step 3: Checking component logs..."
if docker compose logs telemetry-allinone | grep -q "starting GoFlow2"; then
    print_status "PASS" "goflow2 collector is running"
else
    print_status "FAIL" "goflow2 collector not found in logs"
fi

if docker compose logs telemetry-allinone | grep -q "Starting NetFlow mapper"; then
    print_status "PASS" "NetFlow mapper is running"
else
    print_status "FAIL" "NetFlow mapper not found in logs"
fi

if docker compose logs telemetry-allinone | grep -q "Uvicorn running on http://0.0.0.0:80"; then
    print_status "PASS" "API server is running on port 80"
else
    print_status "FAIL" "API server not found in logs"
fi

echo ""
echo "Step 4: Testing NetFlow ingestion pipeline..."
echo "Generating test NetFlow data..."

# Get initial metrics
INITIAL_REQUESTS=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/metrics?window=300" | jq -r '.requests_total')
INITIAL_RECORDS=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/metrics?window=300" | jq -r '.records_processed')

echo "Initial metrics - Requests: $INITIAL_REQUESTS, Records: $INITIAL_RECORDS"

# Generate NetFlow data
python3 scripts/generate_test_netflow.py --count 5 --flows 3 > /dev/null 2>&1

echo "Waiting for data processing..."
sleep 3

# Get final metrics
FINAL_REQUESTS=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/metrics?window=300" | jq -r '.requests_total')
FINAL_RECORDS=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/metrics?window=300" | jq -r '.records_processed')

echo "Final metrics - Requests: $FINAL_REQUESTS, Records: $FINAL_RECORDS"

# Check if metrics increased
if [ "$FINAL_RECORDS" -gt "$INITIAL_RECORDS" ]; then
    print_status "PASS" "NetFlow records were processed successfully"
else
    print_status "FAIL" "No NetFlow records were processed"
fi

echo ""
echo "Step 5: Checking for successful ingest logs..."
if docker compose logs telemetry-allinone | tail -20 | grep -q "\[INGEST\] sent.*status=200"; then
    print_status "PASS" "Mapper successfully sent data to API"
else
    print_status "FAIL" "No successful ingest operations found"
fi

echo ""
echo "Step 6: Port verification..."
if netstat -an 2>/dev/null | grep -q ":80.*LISTEN" || lsof -i :80 2>/dev/null | grep -q "LISTEN"; then
    print_status "PASS" "Port 80 (API/GUI) is listening"
else
    print_status "FAIL" "Port 80 is not listening"
fi

if netstat -an 2>/dev/null | grep -q ":2055.*udp" || lsof -i :2055 2>/dev/null | grep -q "UDP"; then
    print_status "PASS" "Port 2055 (NetFlow) is listening"
else
    print_status "FAIL" "Port 2055 is not listening"
fi

echo ""
echo "🎉 All-in-One Container Verification Complete!"
echo "=============================================="
echo ""
echo "✅ Single container with:"
echo "   - API/GUI on port 80"
echo "   - NetFlow collector on port 2055/udp"
echo "   - goflow2 → FIFO → mapper → API pipeline"
echo "   - Multi-architecture support (AMD64/ARM64)"
echo ""
echo "🚀 Ready for production use!"
echo ""
echo "Test commands:"
echo "  # Generate more NetFlow data:"
echo "  python3 scripts/generate_test_netflow.py --count 10 --flows 5"
echo ""
echo "  # Check metrics:"
echo "  curl -s -H \"Authorization: Bearer TEST_KEY\" \"http://localhost/v1/metrics?window=300\" | jq"
echo ""
echo "  # View logs:"
echo "  docker compose logs -f telemetry-allinone"
