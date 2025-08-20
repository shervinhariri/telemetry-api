#!/usr/bin/env bash
set -euo pipefail

API=${API:-http://localhost}
KEY=${KEY:-TEST_KEY}

say() { printf "\n\033[1m== %s ==\033[0m\n" "$*"; }

say "Phase B4 - Simplified Metrics Test"
echo "Testing basic metrics functionality without admission control"

say "Baseline metrics snapshot"
M_BEFORE=$(curl -s "$API/v1/metrics/prometheus" | grep -E 'telemetry_(blocked_source_total|records_parsed_total|fifo_dropped_total)' || true)
echo "$M_BEFORE"

say "Happy path ingest (should be 200)"
for i in {1..3}; do
    RESPONSE=$(curl -s -X POST "$API/v1/ingest" \
      -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
      -d "{\"collector_id\":\"test-simple-$i\",\"format\":\"flows.v1\",\"records\":[{\"ts\":$i,\"src_ip\":\"1.1.1.$i\",\"dst_ip\":\"2.2.2.$i\"}]}")
    
    if echo "$RESPONSE" | jq -e '.accepted' > /dev/null 2>&1; then
        echo "   Request $i: ✅ $(echo "$RESPONSE" | jq -r '.accepted') records accepted"
    else
        echo "   Request $i: ❌ Failed: $RESPONSE"
    fi
done

say "Test UDP metrics endpoint"
UDP_RESPONSE=$(curl -s -X POST "$API/v1/admin/metrics/udp" \
  -H "Authorization: Bearer ADMIN_SOURCES_TEST" -H "Content-Type: application/json" \
  -d '{"udp_packets_received":5,"records_parsed":4}')

if echo "$UDP_RESPONSE" | jq -e '.status == "ok"' > /dev/null 2>&1; then
    echo "✅ UDP metrics endpoint working: $UDP_RESPONSE"
else
    echo "❌ UDP metrics endpoint failed: $UDP_RESPONSE"
fi

say "Final metrics snapshot"
M_AFTER=$(curl -s "$API/v1/metrics/prometheus" | grep -E 'telemetry_(blocked_source_total|records_parsed_total|fifo_dropped_total)' || true)
echo "$M_AFTER"

say "Assertions"
# Check that records_parsed_total increased
BEFORE_PARSED=$(echo "$M_BEFORE" | grep "telemetry_records_parsed_total" | grep -v "#" | awk '{print $2}' | head -1 || echo "0")
AFTER_PARSED=$(echo "$M_AFTER" | grep "telemetry_records_parsed_total" | grep -v "#" | awk '{print $2}' | head -1 || echo "0")

BEFORE_PARSED_INT=$(echo "$BEFORE_PARSED" | cut -d. -f1)
AFTER_PARSED_INT=$(echo "$AFTER_PARSED" | cut -d. -f1)

if [ "$AFTER_PARSED_INT" -gt "$BEFORE_PARSED_INT" ]; then
    echo "✅ Records parsed metric increased from $BEFORE_PARSED to $AFTER_PARSED"
else
    echo "❌ Records parsed metric did not increase (before: $BEFORE_PARSED, after: $AFTER_PARSED)"
    exit 1
fi

# Check that UDP packets metric is available
UDP_PACKETS=$(echo "$M_AFTER" | grep "telemetry_udp_packets_received_total" | grep -v "#" | awk '{print $2}' | head -1 || echo "0")
if [ "$UDP_PACKETS" != "0" ]; then
    echo "✅ UDP packets metric is recording: $UDP_PACKETS"
else
    echo "❌ UDP packets metric is zero: $UDP_PACKETS"
fi

say "DONE. Basic metrics functionality verified."
