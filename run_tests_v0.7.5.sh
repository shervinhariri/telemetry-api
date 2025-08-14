#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:80}"
API_KEY="${API_KEY:-TEST_KEY}"

echo "=== Telemetry API v0.7.5 Test Suite ==="
echo "Base URL: $BASE_URL"
echo "API Key: $API_KEY"
echo ""

echo "== 1. Health Check =="
curl -sS "$BASE_URL/v1/health" | jq . || true
echo ""

echo "== 2. Version Check =="
curl -sS "$BASE_URL/v1/version" | jq . || true
echo ""

echo "== 3. System Info =="
curl -sS "$BASE_URL/v1/system" | jq . || true
echo ""

echo "== 4. Lookup Test =="
curl -sS -X POST "$BASE_URL/v1/lookup" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  --data '{"ip":"8.8.8.8"}' | jq . || true
echo ""

echo "== 5. Ingest Test =="
curl -sS -X POST "$BASE_URL/v1/ingest" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  --data @ingest_sample.json | jq . || true
echo ""

echo "== 6. Metrics Check =="
curl -sS "$BASE_URL/v1/metrics" | jq '.records_processed, .totals.threat_matches, .totals.risk_count' || true
echo ""

echo "== 7. Requests Summary =="
curl -sS "$BASE_URL/v1/admin/requests/summary" | jq . || true
echo ""

echo "== 8. Requests List =="
curl -sS "$BASE_URL/v1/admin/requests" | jq '.items | length' || true
echo ""

echo "== 9. Negative Tests =="
echo "Testing 401 (no auth):"
curl -sS -w "Status: %{http_code}\n" "$BASE_URL/v1/metrics" || true
echo ""

echo "== 10. Load Test (5 requests) =="
for i in {1..5}; do
  echo "Request $i:"
  curl -sS -X POST "$BASE_URL/v1/ingest" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    --data "[{\"ts\": $(date +%s), \"src_ip\": \"192.168.1.$i\", \"dst_ip\": \"8.8.8.8\", \"src_port\": 12345, \"dst_port\": 53, \"proto\": \"udp\", \"bytes\": 84, \"packets\": 1, \"app\": \"dns\"}]" | jq . || true
done
echo ""

echo "== 11. Final Metrics =="
curl -sS "$BASE_URL/v1/metrics" | jq '.records_processed, .totals.threat_matches, .totals.risk_count' || true
echo ""

echo "=== Test Complete ==="
echo "Open GUI at: $BASE_URL"
echo "Check all tabs: Dashboard, Requests, System, Logs"
