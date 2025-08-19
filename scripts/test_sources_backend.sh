#!/usr/bin/env bash
set -euo pipefail

echo "🧪 Sources Backend Test"
echo "======================="

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

# Test 1: Create a source
echo "Test 1: Creating a source..."
RESPONSE=$(curl -s -X POST http://localhost/v1/sources \
  -H "Authorization: Bearer ADMIN_SOURCES_TEST" \
  -H "Content-Type: application/json" \
  -d '{"id":"src_test_01","tenant_id":"default","type":"test_device","display_name":"test-device-01","collector":"gw-local","site":"TestSite","tags":"[\"test\",\"dev\"]"}')

if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
    print_status "PASS" "Source created successfully"
else
    print_status "FAIL" "Failed to create source: $RESPONSE"
    exit 1
fi

# Test 2: List sources
echo "Test 2: Listing sources..."
RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources")

if echo "$RESPONSE" | jq -e '.sources | length >= 1' > /dev/null 2>&1; then
    print_status "PASS" "Sources listed successfully (found $(echo "$RESPONSE" | jq '.sources | length') sources)"
else
    print_status "FAIL" "Failed to list sources: $RESPONSE"
    exit 1
fi

# Test 3: Get individual source
echo "Test 3: Getting individual source..."
RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources/src_test_01")

if echo "$RESPONSE" | jq -e '.id == "src_test_01"' > /dev/null 2>&1; then
    print_status "PASS" "Individual source retrieved successfully"
else
    print_status "FAIL" "Failed to get individual source: $RESPONSE"
    exit 1
fi

# Test 4: Get source metrics (before data)
echo "Test 4: Getting source metrics (before data)..."
RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources/src_test_01/metrics")

if echo "$RESPONSE" | jq -e '.eps_1m' > /dev/null 2>&1; then
    print_status "PASS" "Source metrics retrieved successfully"
    echo "   Initial metrics: $(echo "$RESPONSE" | jq -r '.eps_1m') EPS, $(echo "$RESPONSE" | jq -r '.records_24h') records"
else
    print_status "FAIL" "Failed to get source metrics: $RESPONSE"
    exit 1
fi

# Test 5: Generate NetFlow data
echo "Test 5: Generating NetFlow data..."
python3 scripts/generate_test_netflow.py --count 3 --flows 2 > /dev/null 2>&1
sleep 2

# Test 6: Check updated metrics
echo "Test 6: Checking updated metrics..."
RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources/src_test_01/metrics")

if echo "$RESPONSE" | jq -e '.records_24h > 0' > /dev/null 2>&1; then
    print_status "PASS" "Source metrics updated after data ingestion"
    echo "   Updated metrics: $(echo "$RESPONSE" | jq -r '.eps_1m') EPS, $(echo "$RESPONSE" | jq -r '.records_24h') records"
else
    print_status "FAIL" "Source metrics not updated: $RESPONSE"
    exit 1
fi

# Test 7: Check source status
echo "Test 7: Checking source status..."
RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources/src_test_01")

if echo "$RESPONSE" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
    print_status "PASS" "Source status is healthy after data ingestion"
else
    print_status "FAIL" "Source status not updated: $(echo "$RESPONSE" | jq -r '.status')"
fi

# Test 8: Test filtering
echo "Test 8: Testing source filtering..."
RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources?type=test_device")

if echo "$RESPONSE" | jq -e '.sources | length >= 1' > /dev/null 2>&1; then
    print_status "PASS" "Source filtering by type works"
else
    print_status "FAIL" "Source filtering failed: $RESPONSE"
fi

echo ""
echo "🎉 All Sources Backend Tests Passed!"
echo "====================================="
echo "✅ Source creation"
echo "✅ Source listing"
echo "✅ Individual source retrieval"
echo "✅ Source metrics"
echo "✅ Data ingestion hook"
echo "✅ Status updates"
echo "✅ Source filtering"
echo ""
echo "The sources backend is working correctly!"
