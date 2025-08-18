#!/usr/bin/env bash
set -euo pipefail

API="${API_BASE_URL:-http://localhost:80}"
KEY="${API_KEY:-TEST_KEY}"

pass(){ echo "✅ $1"; }
fail(){ echo "❌ $1"; exit 1; }

curl -sf "$API/v1/health" >/dev/null && pass "Health OK"

curl -s -o /dev/null -w "%{http_code}\n" -X POST "$API/v1/ingest" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"collector_id":"tester","format":"flows.v1","records":[{"ts":1723351200.456,"src_ip":"10.0.0.10","dst_ip":"8.8.8.8","src_port":54000,"dst_port":53,"protocol":"udp","bytes":120,"packets":1}]}' \
  | grep -qE "200" && pass "Valid low risk accepted"

code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/v1/ingest" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"collector_id":"tester","format":"flows.v1","records":[{"ts":1723351202.123","src_ip":"10.0.0.12","src_port":55555,"dst_port":80,"protocol":"tcp","bytes":256,"packets":2}]}')
[[ "$code" == "400" ]] && pass "Missing field rejected (400)" || fail "Missing field expected 400, got $code"

curl -s -H "Authorization: Bearer $KEY" "$API/v1/admin/requests?exclude_monitoring=true&limit=5" \
  | jq '.items[] | {id, status, latency_ms, fitness, path}'

curl -s -H "Authorization: Bearer $KEY" "$API/v1/metrics?window=900" | jq 'to_entries | .[0:10]'


