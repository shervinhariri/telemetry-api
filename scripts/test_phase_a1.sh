#!/usr/bin/env bash
set -euo pipefail

echo "🧪 Phase A1 - Source Schema Extension Test"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Test 1: Verify new fields are visible in API response
echo "Test 1: Verifying new security fields are visible..."

RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" http://localhost/v1/sources | jq '.sources[0] | {allowed_ips, status, max_eps, block_on_exceed}')

if echo "$RESPONSE" | jq -e '.allowed_ips' > /dev/null 2>&1 && \
   echo "$RESPONSE" | jq -e '.status' > /dev/null 2>&1 && \
   echo "$RESPONSE" | jq -e '.max_eps' > /dev/null 2>&1 && \
   echo "$RESPONSE" | jq -e '.block_on_exceed' > /dev/null 2>&1; then
    print_status "PASS" "All new security fields are visible in API response"
    echo "   Response: $RESPONSE"
else
    print_status "FAIL" "Missing security fields in API response"
    exit 1
fi

# Test 2: Create source with security fields
echo "Test 2: Creating source with security fields..."

TEST_ID="src_a1_test_$(date +%s)"
CREATE_RESPONSE=$(curl -s -X POST http://localhost/v1/sources \
  -H "Authorization: Bearer ADMIN_SOURCES_TEST" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\":\"$TEST_ID\",
    \"tenant_id\":\"default\",
    \"type\":\"a1_test\",
    \"display_name\":\"a1-test-01\",
    \"collector\":\"gw-local\",
    \"site\":\"A1Test\",
    \"tags\":\"[\\\"a1\\\",\\\"test\\\"]\",
    \"status\":\"enabled\",
    \"allowed_ips\":\"[\\\"192.168.1.0/24\\\",\\\"10.0.0.0/8\\\"]\",
    \"max_eps\":50,
    \"block_on_exceed\":false
  }")

if echo "$CREATE_RESPONSE" | jq -e ".id == \"$TEST_ID\"" > /dev/null 2>&1; then
    print_status "PASS" "Source created successfully with security fields"
else
    print_status "FAIL" "Failed to create source with security fields: $CREATE_RESPONSE"
    exit 1
fi

# Test 3: Verify security fields were saved correctly
echo "Test 3: Verifying security fields were saved correctly..."

READ_RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources/$TEST_ID")

ALLOWED_IPS=$(echo "$READ_RESPONSE" | jq -r '.allowed_ips')
STATUS=$(echo "$READ_RESPONSE" | jq -r '.status')
MAX_EPS=$(echo "$READ_RESPONSE" | jq -r '.max_eps')
BLOCK_ON_EXCEED=$(echo "$READ_RESPONSE" | jq -r '.block_on_exceed')

if [ "$ALLOWED_IPS" = '["192.168.1.0/24","10.0.0.0/8"]' ] && \
   [ "$STATUS" = "enabled" ] && \
   [ "$MAX_EPS" = "50" ] && \
   [ "$BLOCK_ON_EXCEED" = "false" ]; then
    print_status "PASS" "Security fields saved correctly"
    echo "   allowed_ips: $ALLOWED_IPS"
    echo "   status: $STATUS"
    echo "   max_eps: $MAX_EPS"
    echo "   block_on_exceed: $BLOCK_ON_EXCEED"
else
    print_status "FAIL" "Security fields not saved correctly"
    echo "   Expected: allowed_ips=[\"192.168.1.0/24\",\"10.0.0.0/8\"], status=enabled, max_eps=50, block_on_exceed=false"
    echo "   Got: allowed_ips=$ALLOWED_IPS, status=$STATUS, max_eps=$MAX_EPS, block_on_exceed=$BLOCK_ON_EXCEED"
    exit 1
fi

# Test 4: Verify health_status vs status distinction
echo "Test 4: Verifying health_status vs status distinction..."

HEALTH_STATUS=$(echo "$READ_RESPONSE" | jq -r '.health_status')
SECURITY_STATUS=$(echo "$READ_RESPONSE" | jq -r '.status')

if [ "$HEALTH_STATUS" = "stale" ] && [ "$SECURITY_STATUS" = "enabled" ]; then
    print_status "PASS" "health_status and status are distinct fields"
    echo "   health_status: $HEALTH_STATUS (operational health)"
    echo "   status: $SECURITY_STATUS (security enabled/disabled)"
else
    print_status "FAIL" "health_status and status are not distinct"
    echo "   health_status: $HEALTH_STATUS"
    echo "   status: $SECURITY_STATUS"
    exit 1
fi

# Test 5: Test default values for optional fields
echo "Test 5: Testing default values for optional fields..."

DEFAULT_ID="src_defaults_test_$(date +%s)"
DEFAULT_RESPONSE=$(curl -s -X POST http://localhost/v1/sources \
  -H "Authorization: Bearer ADMIN_SOURCES_TEST" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\":\"$DEFAULT_ID\",
    \"tenant_id\":\"default\",
    \"type\":\"defaults_test\",
    \"display_name\":\"defaults-test-01\",
    \"collector\":\"gw-local\"
  }")

DEFAULT_STATUS=$(echo "$DEFAULT_RESPONSE" | jq -r '.status')
DEFAULT_ALLOWED_IPS=$(echo "$DEFAULT_RESPONSE" | jq -r '.allowed_ips')
DEFAULT_MAX_EPS=$(echo "$DEFAULT_RESPONSE" | jq -r '.max_eps')
DEFAULT_BLOCK_ON_EXCEED=$(echo "$DEFAULT_RESPONSE" | jq -r '.block_on_exceed')

if [ "$DEFAULT_STATUS" = "enabled" ] && \
   [ "$DEFAULT_ALLOWED_IPS" = "[]" ] && \
   [ "$DEFAULT_MAX_EPS" = "0" ] && \
   [ "$DEFAULT_BLOCK_ON_EXCEED" = "true" ]; then
    print_status "PASS" "Default values applied correctly"
    echo "   status: $DEFAULT_STATUS (default: enabled)"
    echo "   allowed_ips: $DEFAULT_ALLOWED_IPS (default: [])"
    echo "   max_eps: $DEFAULT_MAX_EPS (default: 0)"
    echo "   block_on_exceed: $DEFAULT_BLOCK_ON_EXCEED (default: true)"
else
    print_status "FAIL" "Default values not applied correctly"
    exit 1
fi

# Test 6: Verify all sources show new fields
echo "Test 6: Verifying all sources show new fields..."

ALL_SOURCES_RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" http://localhost/v1/sources)
SOURCES_COUNT=$(echo "$ALL_SOURCES_RESPONSE" | jq '.sources | length')

print_status "INFO" "Checking $SOURCES_COUNT sources for new fields..."

MISSING_FIELDS=0
for i in $(seq 0 $((SOURCES_COUNT - 1))); do
    SOURCE_ID=$(echo "$ALL_SOURCES_RESPONSE" | jq -r ".sources[$i].id")
    SOURCE=$(echo "$ALL_SOURCES_RESPONSE" | jq ".sources[$i]")
    
    # Check each field individually and report which ones are missing
    MISSING_FIELDS_FOR_SOURCE=0
    if ! echo "$SOURCE" | jq 'has("allowed_ips")' | grep -q "true"; then
        echo "   Source $i ($SOURCE_ID): ❌ Missing allowed_ips"
        MISSING_FIELDS_FOR_SOURCE=1
    fi
    if ! echo "$SOURCE" | jq 'has("status")' | grep -q "true"; then
        echo "   Source $i ($SOURCE_ID): ❌ Missing status"
        MISSING_FIELDS_FOR_SOURCE=1
    fi
    if ! echo "$SOURCE" | jq 'has("max_eps")' | grep -q "true"; then
        echo "   Source $i ($SOURCE_ID): ❌ Missing max_eps"
        MISSING_FIELDS_FOR_SOURCE=1
    fi
    if ! echo "$SOURCE" | jq 'has("block_on_exceed")' | grep -q "true"; then
        echo "   Source $i ($SOURCE_ID): ❌ Missing block_on_exceed"
        MISSING_FIELDS_FOR_SOURCE=1
    fi
    
    if [ $MISSING_FIELDS_FOR_SOURCE -eq 0 ]; then
        echo "   Source $i ($SOURCE_ID): ✅ All fields present"
    else
        MISSING_FIELDS=$((MISSING_FIELDS + 1))
    fi
done

if [ $MISSING_FIELDS -eq 0 ]; then
    print_status "PASS" "All sources have the new security fields"
else
    print_status "FAIL" "$MISSING_FIELDS sources missing security fields"
    exit 1
fi

echo ""
echo "🎉 Phase A1 - Source Schema Extension Complete!"
echo "==============================================="
echo "✅ New security fields added to database schema"
echo "✅ Source model updated with security fields"
echo "✅ Pydantic schemas updated for validation"
echo "✅ API endpoints handle new fields correctly"
echo "✅ Default values working properly"
echo "✅ health_status vs status distinction maintained"
echo ""
echo "📋 New Fields Added:"
echo "   - status: 'enabled' | 'disabled' (default: 'enabled')"
echo "   - allowed_ips: JSON array of CIDR strings (default: [])"
echo "   - max_eps: integer, 0 = unlimited (default: 0)"
echo "   - block_on_exceed: boolean (default: true)"
echo ""
echo "🔧 Database Changes:"
echo "   - Renamed existing 'status' column to 'health_status'"
echo "   - Added new 'status' column for security enable/disable"
echo "   - Added 'allowed_ips', 'max_eps', 'block_on_exceed' columns"
echo ""
echo "🚀 Ready for Phase A2 - Admin helpers and admission testing!"
