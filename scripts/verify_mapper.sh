#!/bin/bash
set -euo pipefail

echo "🧪 NetFlow Mapper Verification Test"
echo "==================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Bring up API + collector
echo -e "${YELLOW}Step 1: Bringing up API + collector...${NC}"
docker compose up -d api collector
sleep 5

# Step 2: Start mapper (after Cursor adds it)
echo -e "${YELLOW}Step 2: Starting mapper...${NC}"
docker compose logs -f collector | grep "NETFLOW_V" | sed 's/.*| //' | docker compose run --rm -T mapper python3 nf2ingest.py &
MAPPER_PID=$!
sleep 2

# Step 3: Generate some flows
echo -e "${YELLOW}Step 3: Generating test NetFlow data...${NC}"
python3 scripts/generate_test_netflow.py --count 5 --flows 3

# Step 4: Watch mapper/collector logs
echo -e "${YELLOW}Step 4: Checking logs...${NC}"
echo "Collector logs (last 5 lines):"
docker compose logs collector | grep "NETFLOW_V" | tail -5 | sed 's/.*| //' | head -3

echo ""
echo "Mapper logs:"
docker compose logs mapper 2>/dev/null | tail -5 || echo "No mapper logs in docker compose"

# Step 5: Confirm metrics roll up through the API
echo -e "${YELLOW}Step 5: Checking API metrics...${NC}"
METRICS=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/metrics?window=300")
REQUESTS_TOTAL=$(echo "$METRICS" | jq -r '.requests_total')
RECORDS_PROCESSED=$(echo "$METRICS" | jq -r '.records_processed')
EPS=$(echo "$METRICS" | jq -r '.eps')

echo "API Metrics:"
echo "  requests_total: $REQUESTS_TOTAL"
echo "  records_processed: $RECORDS_PROCESSED"
echo "  eps: $EPS"

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

# Cleanup
echo ""
echo -e "${YELLOW}Cleaning up...${NC}"
kill $MAPPER_PID 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ Verification test completed!${NC}"
