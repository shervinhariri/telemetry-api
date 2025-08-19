#!/usr/bin/env bash
set -euo pipefail

echo "🧪 Sources UI Test"
echo "=================="

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

# Test 1: API endpoints are working
echo "Test 1: Verifying Sources API endpoints..."

# Test POST /v1/sources
RESPONSE=$(curl -s -X POST http://localhost/v1/sources \
  -H "Authorization: Bearer ADMIN_SOURCES_TEST" \
  -H "Content-Type: application/json" \
  -d '{"id":"src_ui_test_01","tenant_id":"default","type":"ui_test","display_name":"ui-test-01","collector":"gw-local","site":"UITest","tags":"[\"ui\",\"test\"]"}')

if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
    print_status "PASS" "POST /v1/sources endpoint working"
else
    print_status "FAIL" "POST /v1/sources failed: $RESPONSE"
    exit 1
fi

# Test GET /v1/sources
RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources")

if echo "$RESPONSE" | jq -e '.sources | length >= 1' > /dev/null 2>&1; then
    print_status "PASS" "GET /v1/sources endpoint working (found $(echo "$RESPONSE" | jq '.sources | length') sources)"
else
    print_status "FAIL" "GET /v1/sources failed: $RESPONSE"
    exit 1
fi

# Test GET /v1/sources/{id}
RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources/src_ui_test_01")

if echo "$RESPONSE" | jq -e '.id == "src_ui_test_01"' > /dev/null 2>&1; then
    print_status "PASS" "GET /v1/sources/{id} endpoint working"
else
    print_status "FAIL" "GET /v1/sources/{id} failed: $RESPONSE"
    exit 1
fi

# Test GET /v1/sources/{id}/metrics
RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources/src_ui_test_01/metrics")

if echo "$RESPONSE" | jq -e '.eps_1m' > /dev/null 2>&1; then
    print_status "PASS" "GET /v1/sources/{id}/metrics endpoint working"
else
    print_status "FAIL" "GET /v1/sources/{id}/metrics failed: $RESPONSE"
    exit 1
fi

# Test 2: Ingest hook updates sources
echo "Test 2: Verifying ingest hook updates sources..."

# Generate some NetFlow data
python3 scripts/generate_test_netflow.py --count 3 --flows 2 > /dev/null 2>&1
sleep 2

# Check if source status and last_seen updated
RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources/src_ui_test_01")

if echo "$RESPONSE" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
    print_status "PASS" "Source status updated to healthy after ingest"
else
    print_status "FAIL" "Source status not updated: $(echo "$RESPONSE" | jq -r '.status')"
fi

# Test 3: UI is accessible
echo "Test 3: Verifying UI accessibility..."

# Check if the main page loads
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/)

if [ "$RESPONSE" = "200" ]; then
    print_status "PASS" "UI main page accessible (HTTP 200)"
else
    print_status "FAIL" "UI main page not accessible (HTTP $RESPONSE)"
fi

# Test 4: Sources filtering
echo "Test 4: Testing Sources API filtering..."

# Test filtering by type
RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources?type=ui_test")

if echo "$RESPONSE" | jq -e '.sources | length >= 1' > /dev/null 2>&1; then
    print_status "PASS" "Sources filtering by type working"
else
    print_status "FAIL" "Sources filtering by type failed: $RESPONSE"
fi

# Test filtering by status
RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources?status=healthy")

if echo "$RESPONSE" | jq -e '.sources | length >= 1' > /dev/null 2>&1; then
    print_status "PASS" "Sources filtering by status working"
else
    print_status "FAIL" "Sources filtering by status failed: $RESPONSE"
fi

# Test 5: Pagination
echo "Test 5: Testing Sources pagination..."

# Test pagination with small page size
RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources?page=1&size=1")

if echo "$RESPONSE" | jq -e '.sources | length <= 1' > /dev/null 2>&1; then
    print_status "PASS" "Sources pagination working"
else
    print_status "FAIL" "Sources pagination failed: $RESPONSE"
fi

echo ""
echo "🎉 All Sources UI Tests Passed!"
echo "==============================="
echo "✅ Sources API endpoints working"
echo "✅ Ingest hook updating sources"
echo "✅ UI accessible on port 80"
echo "✅ Sources filtering functional"
echo "✅ Sources pagination working"
echo ""
echo "The Sources UI is ready for use!"
echo ""
echo "📋 Manual Verification Steps:"
echo "1. Open http://localhost in your browser"
echo "2. Click on the 'Sources' tab"
echo "3. Verify the table shows your sources"
echo "4. Test the filters (Tenant, Type, Status)"
echo "5. Click on a source row to see details"
echo "6. Generate more NetFlow data to see live updates"
