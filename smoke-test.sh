#!/usr/bin/env bash
set -euo pipefail

API=${API:-http://localhost:8080}
KEY=${KEY:-TEST_KEY}

echo "🧪 Telemetry API Smoke Test"
echo "API: $API"
echo "KEY: ${KEY:0:8}..."
echo ""

check() {
    echo "→ $1"
    response=$(curl -s -H "Authorization: Bearer $KEY" "$API$2")
    
    if echo "$response" | jq -e . >/dev/null 2>&1; then
        # Valid JSON response
        if echo "$response" | jq -e '.[0]?, .summary?, .items?, .eps?' >/dev/null 2>&1; then
            echo "  ✓ OK - Data found"
            echo "$response" | jq -r '.[0]?, .summary? // .items? // .eps? // .' | head -3
        else
            echo "  ✓ OK - Empty response"
        fi
    else
        echo "  ✗ FAIL - Invalid JSON or error"
        echo "$response" | head -3
    fi
    echo ""
}

check "Health" "/v1/health"
check "System" "/v1/system"
check "Metrics" "/v1/metrics"
check "Requests (15m)" "/v1/api/requests?limit=50&window=15m"
check "Requests (24h)" "/v1/api/requests?limit=500&window=24h"

echo "✅ Smoke test completed"
