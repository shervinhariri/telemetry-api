#!/bin/bash
set -euo pipefail

echo "🧪 All-in-One Container Verification Test"
echo "========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Build & run
echo -e "${YELLOW}Step 1: Building and running all-in-one container...${NC}"
docker compose down -v 2>/dev/null || true
docker build -t shvin/telemetry-api:allinone-latest .
docker compose up -d telemetry-allinone

echo "Waiting for container to start..."
sleep 10

# Step 2: API sanity
echo -e "${YELLOW}Step 2: API sanity checks...${NC}"
echo "Health check:"
HEALTH_RESPONSE=$(curl -s http://localhost/v1/health || echo "FAILED")
if [[ "$HEALTH_RESPONSE" == "FAILED" ]]; then
    echo -e "${RED}❌ Health check failed${NC}"
    docker compose logs telemetry-allinone
    exit 1
else
    echo -e "${GREEN}✅ Health check passed${NC}"
    echo "$HEALTH_RESPONSE"
fi

echo ""
echo "Version check:"
VERSION_RESPONSE=$(curl -s http://localhost/v1/version || echo "FAILED")
if [[ "$VERSION_RESPONSE" == "FAILED" ]]; then
    echo -e "${RED}❌ Version check failed${NC}"
else
    echo -e "${GREEN}✅ Version check passed${NC}"
    echo "$VERSION_RESPONSE"
fi

# Step 3: Generate flows
echo -e "${YELLOW}Step 3: Generating test NetFlow data...${NC}"
python3 scripts/generate_test_netflow.py --count 5 --flows 3

echo "Waiting for processing..."
sleep 5

# Step 4: Confirm ingest/metrics
echo -e "${YELLOW}Step 4: Checking API metrics...${NC}"
METRICS=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/metrics?window=300")
REQUESTS_TOTAL=$(echo "$METRICS" | jq -r '.requests_total')
RECORDS_PROCESSED=$(echo "$METRICS" | jq -r '.records_processed')
EPS=$(echo "$METRICS" | jq -r '.eps')

echo "API Metrics:"
echo "  requests_total: $REQUESTS_TOTAL"
echo "  records_processed: $RECORDS_PROCESSED"
echo "  eps: $EPS"

# Step 5: Check container logs
echo -e "${YELLOW}Step 5: Checking container logs...${NC}"
echo "Container logs (last 20 lines):"
docker compose logs telemetry-allinone | tail -20

# Verification
echo ""
echo -e "${YELLOW}Verification Results:${NC}"

if [ "$REQUESTS_TOTAL" -gt 0 ]; then
    echo -e "${GREEN}✅ requests_total increased${NC}"
else
    echo -e "${RED}❌ requests_total not increased${NC}"
fi

if [ "$RECORDS_PROCESSED" -gt 0 ]; then
    echo -e "${GREEN}✅ records_processed increased${NC}"
else
    echo -e "${RED}❌ records_processed not increased${NC}"
fi

if [ "$EPS" -gt 0 ]; then
    echo -e "${GREEN}✅ eps is non-zero${NC}"
else
    echo -e "${RED}❌ eps is zero${NC}"
fi

# Check for all three components in logs
echo ""
echo -e "${YELLOW}Component Status:${NC}"
if docker compose logs telemetry-allinone | grep -q "Starting goflow2"; then
    echo -e "${GREEN}✅ goflow2 started${NC}"
else
    echo -e "${RED}❌ goflow2 not found in logs${NC}"
fi

if docker compose logs telemetry-allinone | grep -q "Starting mapper"; then
    echo -e "${GREEN}✅ mapper started${NC}"
else
    echo -e "${RED}❌ mapper not found in logs${NC}"
fi

if docker compose logs telemetry-allinone | grep -q "Starting API"; then
    echo -e "${GREEN}✅ API started${NC}"
else
    echo -e "${RED}❌ API not found in logs${NC}"
fi

# Check for successful ingest
if docker compose logs telemetry-allinone | grep -q "\[INGEST\] sent.*status=200"; then
    echo -e "${GREEN}✅ Mapper successfully sent data to API${NC}"
else
    echo -e "${RED}❌ No successful ingest found in logs${NC}"
fi

echo ""
echo -e "${GREEN}✅ All-in-one verification test completed!${NC}"
echo ""
echo "Container is running with:"
echo "  API/GUI: http://localhost/"
echo "  NetFlow collector: UDP/2055"
echo "  Health check: http://localhost/v1/health"
echo "  Metrics: http://localhost/v1/metrics"
