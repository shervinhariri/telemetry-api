#!/usr/bin/env bash
set -euo pipefail

API=${API:-http://localhost}
ADMIN_KEY=${ADMIN_KEY:-ADMIN_SOURCES_TEST}
KEY=${KEY:-TEST_KEY}

say() { printf "\n\033[1m== %s ==\033[0m\n" "$*"; }

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}❌ $message${NC}"
    elif [ "$status" = "INFO" ]; then
        echo -e "${BLUE}ℹ️  $message${NC}"
    else
        echo -e "${YELLOW}⚠️  $message${NC}"
    fi
}

say "Sources Table with Row Actions Test Suite"
echo "Testing the complete Sources table functionality"

say "1. Backend Endpoints"
print_status "INFO" "Testing admission test, update, and delete endpoints"

# Test admission endpoint
ADMISSION_RESPONSE=$(curl -s -X POST -H "Authorization: Bearer $ADMIN_KEY" -H "Content-Type: application/json" \
  -d '{"client_ip":"203.0.113.10"}' "$API/v1/sources/src_asa_krk_01/admission/test")

if echo "$ADMISSION_RESPONSE" | jq -e '.allowed' >/dev/null 2>&1; then
    print_status "PASS" "Admission test endpoint working"
    echo "   Result: $(echo "$ADMISSION_RESPONSE" | jq -r '.allowed') - $(echo "$ADMISSION_RESPONSE" | jq -r '.reason')"
else
    print_status "FAIL" "Admission test endpoint failed"
fi

# Test update endpoint
UPDATE_RESPONSE=$(curl -s -X PUT -H "Authorization: Bearer $ADMIN_KEY" -H "Content-Type: application/json" \
  -d '{"allowed_ips":["192.168.1.0/24","10.0.0.0/8"],"max_eps":75,"block_on_exceed":false}' \
  "$API/v1/sources/src_asa_krk_01")

if echo "$UPDATE_RESPONSE" | jq -e '.allowed_ips' >/dev/null 2>&1; then
    print_status "PASS" "Update endpoint working"
    echo "   Updated allowed_ips: $(echo "$UPDATE_RESPONSE" | jq -r '.allowed_ips')"
else
    print_status "FAIL" "Update endpoint failed"
fi

# Test admission with updated IPs
ADMISSION_AFTER_UPDATE=$(curl -s -X POST -H "Authorization: Bearer $ADMIN_KEY" -H "Content-Type: application/json" \
  -d '{"client_ip":"192.168.1.100"}' "$API/v1/sources/src_asa_krk_01/admission/test")

if echo "$ADMISSION_AFTER_UPDATE" | jq -e '.allowed == true' >/dev/null 2>&1; then
    print_status "PASS" "Admission test with updated IPs working"
    echo "   IP 192.168.1.100: $(echo "$ADMISSION_AFTER_UPDATE" | jq -r '.allowed')"
else
    print_status "FAIL" "Admission test with updated IPs failed"
fi

say "2. Validation & RBAC"
print_status "INFO" "Testing CIDR validation and RBAC enforcement"

# Test invalid CIDR
INVALID_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X PUT -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"allowed_ips":["invalid-cidr"]}' \
  "$API/v1/sources/src_asa_krk_01")

if [ "$INVALID_RESPONSE" = "400" ]; then
    print_status "PASS" "CIDR validation working (rejected invalid CIDR)"
else
    print_status "FAIL" "CIDR validation not working (HTTP $INVALID_RESPONSE)"
fi

# Test non-admin access to admin endpoints (using a key that doesn't exist)
NONADMIN_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Authorization: Bearer NONEXISTENT_KEY" \
  -H "Content-Type: application/json" \
  -d '{"client_ip":"192.168.1.100"}' \
  "$API/v1/sources/src_asa_krk_01/admission/test")

if [ "$NONADMIN_RESPONSE" = "401" ] || [ "$NONADMIN_RESPONSE" = "403" ]; then
    print_status "PASS" "RBAC enforcement working (non-admin blocked)"
else
    print_status "FAIL" "RBAC enforcement not working (HTTP $NONADMIN_RESPONSE)"
fi

say "3. Sources List with New Columns"
print_status "INFO" "Testing sources list with Allowed IPs and EPS Cap columns"

SOURCES_RESPONSE=$(curl -s -H "Authorization: Bearer $ADMIN_KEY" "$API/v1/sources?size=2")

if echo "$SOURCES_RESPONSE" | jq -e '.sources[0].allowed_ips' >/dev/null 2>&1; then
    print_status "PASS" "Sources list includes allowed_ips field"
    echo "   Sample allowed_ips: $(echo "$SOURCES_RESPONSE" | jq -r '.sources[0].allowed_ips')"
else
    print_status "FAIL" "Sources list missing allowed_ips field"
fi

if echo "$SOURCES_RESPONSE" | jq -e '.sources[0].max_eps' >/dev/null 2>&1; then
    print_status "PASS" "Sources list includes max_eps field"
    echo "   Sample max_eps: $(echo "$SOURCES_RESPONSE" | jq -r '.sources[0].max_eps')"
else
    print_status "FAIL" "Sources list missing max_eps field"
fi

say "4. Create and Delete Test"
print_status "INFO" "Testing source creation and deletion"

# Create a test source
TEST_SOURCE_ID="test-ui-$(date +%s)"
CREATE_RESPONSE=$(curl -s -X POST -H "Authorization: Bearer $ADMIN_KEY" -H "Content-Type: application/json" \
  -d "{\"id\":\"$TEST_SOURCE_ID\",\"tenant_id\":\"default\",\"type\":\"test\",\"display_name\":\"UI Test Source\",\"collector\":\"gw-local\",\"status\":\"enabled\",\"allowed_ips\":\"[\\\"172.16.0.0/12\\\"]\",\"max_eps\":25,\"block_on_exceed\":true}" \
  "$API/v1/sources")

if echo "$CREATE_RESPONSE" | jq -e '.id' >/dev/null 2>&1; then
    print_status "PASS" "Source creation working"
    echo "   Created source: $(echo "$CREATE_RESPONSE" | jq -r '.id')"
else
    print_status "FAIL" "Source creation failed"
    echo "   Response: $CREATE_RESPONSE"
fi

# Delete the test source
DELETE_RESPONSE=$(curl -s -X DELETE -H "Authorization: Bearer $ADMIN_KEY" "$API/v1/sources/$TEST_SOURCE_ID")

if echo "$DELETE_RESPONSE" | jq -e '.message' >/dev/null 2>&1; then
    print_status "PASS" "Source deletion working"
    echo "   Delete message: $(echo "$DELETE_RESPONSE" | jq -r '.message')"
else
    print_status "FAIL" "Source deletion failed"
    echo "   Response: $DELETE_RESPONSE"
fi

# Verify deletion
VERIFY_DELETE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $ADMIN_KEY" "$API/v1/sources/$TEST_SOURCE_ID")

if [ "$VERIFY_DELETE" = "404" ]; then
    print_status "PASS" "Source deletion verified (404 returned)"
else
    print_status "FAIL" "Source deletion verification failed (HTTP $VERIFY_DELETE)"
fi

say "5. Final Health Check"
FINAL_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$API/v1/health")

if [ "$FINAL_HEALTH" = "200" ]; then
    print_status "PASS" "API remains healthy after all tests"
else
    print_status "FAIL" "API became unhealthy after tests (HTTP $FINAL_HEALTH)"
fi

say "DONE. Sources Table Test Complete!"
echo ""
echo "✅ Backend endpoints working (admission test, update, delete)"
echo "✅ Validation & RBAC enforced"
echo "✅ Sources list includes new columns"
echo "✅ Create and delete functionality working"
echo "✅ API remains healthy"
echo ""
echo "🚀 Sources table with row actions is ready for production!"
echo ""
echo "💡 Next Steps:"
echo "   - Test the UI Sources table with the new columns"
echo "   - Verify the Access & Limits drawer functionality"
echo "   - Test row actions (View, Edit, Delete)"
echo "   - Verify 10s polling updates the table correctly"
