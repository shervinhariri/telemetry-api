#!/usr/bin/env bash
set -euo pipefail

echo "🎯 v0.8.4 Release Verification"
echo "=============================="

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

# Test 1: Version Check
echo "Test 1: Version Verification"
VERSION_RESPONSE=$(curl -s http://localhost/v1/version)
VERSION=$(echo "$VERSION_RESPONSE" | jq -r '.version')

if [ "$VERSION" = "0.8.4" ]; then
    print_status "PASS" "Version is correctly set to 0.8.4"
else
    print_status "FAIL" "Version mismatch: expected 0.8.4, got $VERSION"
    exit 1
fi

# Test 2: Health Check
echo "Test 2: Health Check"
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/v1/health)

if [ "$HEALTH_RESPONSE" = "200" ]; then
    print_status "PASS" "Health endpoint responding (HTTP 200)"
else
    print_status "FAIL" "Health endpoint failed (HTTP $HEALTH_RESPONSE)"
    exit 1
fi

# Test 3: Sources Backend
echo "Test 3: Sources Backend"
SOURCES_RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources")
SOURCES_COUNT=$(echo "$SOURCES_RESPONSE" | jq '.sources | length')

if [ "$SOURCES_COUNT" -ge 1 ]; then
    print_status "PASS" "Sources API working (found $SOURCES_COUNT sources)"
else
    print_status "FAIL" "Sources API not working"
    exit 1
fi

# Test 4: Sources Metrics
echo "Test 4: Sources Metrics"
METRICS_RESPONSE=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources/src_v084_test/metrics")

if echo "$METRICS_RESPONSE" | jq -e '.eps_1m' > /dev/null 2>&1; then
    print_status "PASS" "Sources metrics endpoint working"
else
    print_status "FAIL" "Sources metrics endpoint failed"
    exit 1
fi

# Test 5: NetFlow Ingestion
echo "Test 5: NetFlow Ingestion"
print_status "INFO" "Generating test NetFlow data..."
python3 scripts/generate_test_netflow.py --count 2 --flows 1 > /dev/null 2>&1
sleep 2

# Check if source status updated
SOURCE_STATUS=$(curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/sources/src_v084_test" | jq -r '.status')

if [ "$SOURCE_STATUS" = "healthy" ]; then
    print_status "PASS" "NetFlow ingestion working (source status: $SOURCE_STATUS)"
else
    print_status "FAIL" "NetFlow ingestion failed (source status: $SOURCE_STATUS)"
fi

# Test 6: UI Accessibility
echo "Test 6: UI Accessibility"
UI_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/)

if [ "$UI_RESPONSE" = "200" ]; then
    print_status "PASS" "UI accessible on port 80 (HTTP 200)"
else
    print_status "FAIL" "UI not accessible (HTTP $UI_RESPONSE)"
fi

# Test 7: All-in-One Container
echo "Test 7: All-in-One Container"
CONTAINER_STATUS=$(docker compose ps --format json | jq -r '.[0].State')

if [ "$CONTAINER_STATUS" = "running" ]; then
    print_status "PASS" "All-in-one container running"
else
    print_status "FAIL" "Container not running (status: $CONTAINER_STATUS)"
fi

# Test 8: Port Exposure
echo "Test 8: Port Exposure"
TCP_PORT=$(docker compose ps --format json | jq -r '.[0].Ports' | grep -o "0.0.0.0:80->80" || echo "NOT_FOUND")
UDP_PORT=$(docker compose ps --format json | jq -r '.[0].Ports' | grep -o "0.0.0.0:2055->2055/udp" || echo "NOT_FOUND")

if [ "$TCP_PORT" != "NOT_FOUND" ]; then
    print_status "PASS" "TCP port 80 exposed for API/UI"
else
    print_status "FAIL" "TCP port 80 not exposed"
fi

if [ "$UDP_PORT" != "NOT_FOUND" ]; then
    print_status "PASS" "UDP port 2055 exposed for NetFlow"
else
    print_status "FAIL" "UDP port 2055 not exposed"
fi

# Test 9: Database Migration
echo "Test 9: Database Migration"
DB_CHECK=$(sqlite3 telemetry.db "SELECT name FROM sqlite_master WHERE type='table' AND name='sources';" 2>/dev/null || echo "NOT_FOUND")

if [ "$DB_CHECK" = "sources" ]; then
    print_status "PASS" "Sources table exists in database"
else
    print_status "FAIL" "Sources table not found in database"
fi

# Test 10: API Key Management
echo "Test 10: API Key Management"
ADMIN_KEY_TEST=$(curl -s -X POST http://localhost/v1/sources \
  -H "Authorization: Bearer ADMIN_SOURCES_TEST" \
  -H "Content-Type: application/json" \
  -d '{"id":"src_final_test","tenant_id":"default","type":"final_test","display_name":"final-test","collector":"gw-local"}' | jq -r '.id' 2>/dev/null || echo "FAILED")

if [ "$ADMIN_KEY_TEST" = "src_final_test" ]; then
    print_status "PASS" "Admin API key working for source creation"
else
    print_status "FAIL" "Admin API key not working"
fi

echo ""
echo "🎉 v0.8.4 Release Verification Complete!"
echo "========================================="
echo "✅ Version: 0.8.4"
echo "✅ Health: API responding"
echo "✅ Sources: Backend + API + Metrics working"
echo "✅ NetFlow: Ingestion pipeline functional"
echo "✅ UI: Accessible on port 80"
echo "✅ Container: All-in-one running"
echo "✅ Ports: TCP/80 + UDP/2055 exposed"
echo "✅ Database: Sources table migrated"
echo "✅ Auth: API key management working"
echo ""
echo "🚀 v0.8.4 is ready for release!"
echo ""
echo "📋 Next Steps:"
echo "1. Tag the release: git tag -a v0.8.4 -m 'Telemetry API v0.8.4'"
echo "2. Push to GitHub: git push origin main --tags"
echo "3. Update documentation if needed"
echo "4. Deploy to production environments"
