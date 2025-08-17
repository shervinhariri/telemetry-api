#!/usr/bin/env bash
# diagnostics.sh — Deterministic end-to-end checks for Telemetry API + UI
# Usage: bash diagnostics.sh [API_BASE] [API_KEY]
set -euo pipefail
API_BASE="${1:-http://localhost}"
API_KEY="${2:-TEST_KEY}"

echo "==> Using API_BASE=$API_BASE"
echo "==> Health check"
curl -sf "$API_BASE/v1/health" > /dev/null && echo "✓ /v1/health OK"

echo "==> System"
curl -sf "$API_BASE/v1/system" | jq -r '.uptime_s as $u | "✓ /v1/system uptime=\($u)s"'

echo "==> Ingest one small batch to guarantee UI has data"
if [ -f "samples/zeek_conn_small.json" ]; then
  SRC="samples/zeek_conn_small.json"
elif [ -f "samples/zeek_conn.json" ]; then
  SRC="samples/zeek_conn.json"
elif [ -f "./app/samples/zeek_conn.json" ]; then
  SRC="./app/samples/zeek_conn.json"
else
  # Minimal single record payload as fallback
  SRC="/tmp/single.json"
  cat > "$SRC" <<'EOF'
[
  {"ts":"2025-08-16T12:00:00Z","uid":"ui-diag-1","id.orig_h":"10.0.0.10","id.resp_h":"1.1.1.1","proto":"tcp","service":"http","orig_bytes":150,"resp_bytes":200}
]
EOF
fi

curl -s -X POST "$API_BASE/v1/ingest/zeek" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  --data @"$SRC" | jq -r '"✓ ingest accepted: " + ( .processed // .status // "ok")'

echo "==> Poll API surfaces the UI uses (with fresh cache-busting)"
QP="window=15m&nocache=$(date +%s)"
REQ1="$(curl -s -H "Authorization: Bearer $API_KEY" "$API_BASE/v1/api/requests?limit=50&$QP")"
REQ2="$(curl -s -H "Authorization: Bearer $API_KEY" "$API_BASE/v1/api/requests?limit=500&window=24h&nocache=$(date +%s)")"
METR="$(curl -s -H "Authorization: Bearer $API_KEY" "$API_BASE/v1/metrics?window=15m&nocache=$(date +%s)")"

# Basic structural assertions
jq -e 'type=="object" and has("items")' <<<"$REQ1" >/dev/null 2>&1 && echo "✓ /v1/api/requests (15m) returned object with items" || { echo "✗ /v1/api/requests (15m) not object with items"; echo "$REQ1"; exit 1; }
jq -e 'type=="object" and has("items")' <<<"$REQ2" >/dev/null 2>&1 && echo "✓ /v1/api/requests (24h) returned object with items" || { echo "✗ /v1/api/requests (24h) not object with items"; echo "$REQ2"; exit 1; }
jq -e 'type=="object"' <<<"$METR" >/dev/null 2>&1 && echo "✓ /v1/metrics (15m) returned object" || { echo "✗ /v1/metrics (15m) not object"; echo "$METR"; exit 1; }

# Print concise summaries
echo "— requests(15m) count: $(jq '.items | length' <<<"$REQ1")"
echo "— requests(24h) count: $(jq '.items | length' <<<"$REQ2")"
echo "— metrics keys: $(jq -r 'keys | join(\", \")' <<<"$METR")"

echo "==> Version check"
VER="$(curl -s -H "Authorization: Bearer $API_KEY" "$API_BASE/v1/version" || true)"
if [ -n "$VER" ]; then
  echo "$VER" | jq -r '"✓ version: " + ( .version // .tag // "unknown")'
else
  echo "… version endpoint missing (ok if served via UI only)"
fi

cat <<'TXT'

If the UI is still blank:
1) Open DevTools → Network. Refresh page with Cmd+Shift+R.
   - Confirm /v1/api/requests and /v1/metrics are 200, not 401/404/CORS.
2) In Console, run:
   fetch('http://localhost/v1/api/requests?limit=50&window=15m',{headers:{Authorization:'Bearer TEST_KEY'}}).then(r=>r.json()).then(console.log)
3) Check the UI config printed on load: "API Config: {...}".
4) If /v1/* 404s, check the API_PREFIX in the UI config.

TXT
