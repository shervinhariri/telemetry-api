#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://localhost:8080}"
API_KEY="${API_KEY:-TEST_KEY}"
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="$D/data"

pass() { echo -e "✅ $1"; }
fail() { echo -e "❌ $1"; exit 1; }
warn() { echo -e "⚠️  $1"; }

curl_json() {
  local method="$1"; shift
  local path="$1"; shift
  local datafile="${1:-}"; shift || true
  local extra=("$@")
  if [[ -n "$datafile" ]]; then
    curl -sS -w "\n%{http_code}" -X "$method" "$BASE$path" \
         -H "Authorization: Bearer $API_KEY" \
         -H "Content-Type: application/json" \
         --data "@${datafile}"
  else
    curl -sS -w "\n%{http_code}" -X "$method" "$BASE$path" \
         -H "Authorization: Bearer $API_KEY" \
         -H "Content-Type: application/json"
  fi
}

echo "=== Telemetry API Local Testkit ==="
echo "Base: $BASE"
echo "API Key: $API_KEY"
echo ""

# 1) Health (no auth required)
echo "🔍 Testing /v1/health (public endpoint)..."
resp="$(curl -sS -w "\n%{http_code}" "$BASE/v1/health")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]]; then 
    pass "Health OK: $body"; 
else 
    fail "Health FAILED ($code): $body"; 
fi

# 2) Version (Patch 5.1)
echo ""
echo "🔍 Testing /v1/version (Patch 5.1)..."
resp="$(curl_json GET "/v1/version")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]]; then 
    pass "Version: $body"; 
else 
    fail "Version FAILED ($code): $body"; 
fi

# 3) Updates check (Patch 5.1)
echo ""
echo "🔍 Testing /v1/updates/check (Patch 5.1)..."
resp="$(curl_json GET "/v1/updates/check")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]]; then
  if echo "$body" | grep -q '"update_available": *true'; then
    warn "Update available → $body"
  else
    pass "Up-to-date → $body"
  fi
else
  warn "Updates check skipped ($code): $body"
fi

# 4) Output connector configs (Stage 5.1)
echo ""
echo "🔍 Testing /v1/outputs/splunk (Stage 5.1)..."
resp="$(curl_json POST "/v1/outputs/splunk" "$DATA/splunk.json")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]]; then 
    pass "Configured Splunk"; 
else 
    fail "Configure Splunk FAILED ($code): $body"; 
fi

echo ""
echo "🔍 Testing /v1/outputs/elastic (Stage 5.1)..."
resp="$(curl_json POST "/v1/outputs/elastic" "$DATA/elastic.json")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]]; then 
    pass "Configured Elastic"; 
else 
    fail "Configure Elastic FAILED ($code): $body"; 
fi

# 5) Ingest tests (Stage 5 robust pipeline)
echo ""
echo "🔍 Testing /v1/ingest - Raw JSON array..."
resp="$(curl_json POST "/v1/ingest" "$DATA/data_raw_array.json")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]] && echo "$body" | grep -qi '"accepted"'; then 
    pass "Ingest raw array accepted"; 
else 
    fail "Ingest raw array FAILED ($code): $body"; 
fi

echo ""
echo "🔍 Testing /v1/ingest - Wrapped object {records: [...]}..."
resp="$(curl_json POST "/v1/ingest" "$DATA/data_wrapped.json")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]] && echo "$body" | grep -qi '"accepted"'; then 
    pass "Ingest wrapped accepted"; 
else 
    fail "Ingest wrapped FAILED ($code): $body"; 
fi

echo ""
echo "🔍 Testing /v1/ingest - Gzip (Content-Encoding: gzip)..."
resp="$(curl -sS -w "\n%{http_code}" -X POST "$BASE/v1/ingest" \
    -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -H "Content-Encoding: gzip" \
    --data-binary "@$DATA/data_raw_array.json.gz")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]] && echo "$body" | grep -qi '"accepted"'; then 
    pass "Ingest gzip accepted"; 
else 
    fail "Ingest gzip FAILED ($code): $body"; 
fi

echo ""
echo "🔍 Testing /v1/ingest - Invalid record (should return 400)..."
resp="$(curl_json POST "/v1/ingest" "$DATA/data_invalid.json")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "400" ]]; then 
    pass "Bad record correctly rejected (400)"; 
else 
    fail "Bad record expected 400, got $code: $body"; 
fi

# 6) Metrics (optional)
echo ""
echo "🔍 Testing /v1/metrics..."
resp="$(curl -sS -w "\n%{http_code}" "$BASE/v1/metrics")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]]; then
  if echo "$body" | grep -q -E "records_queued|records_processed|ingest"; then
    pass "Metrics available and contain ingest counters"
  else
    warn "Metrics up but no ingest counters detected"
  fi
else
  warn "Metrics endpoint not available ($code)"
fi

echo ""
echo "=== All tests completed ==="
echo "🌐 GUI available at: $BASE"
echo "   Look for the version badge in the top-right corner!"
