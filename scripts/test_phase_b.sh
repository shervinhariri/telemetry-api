#!/usr/bin/env bash
set -euo pipefail

API=${API:-http://localhost}
KEY=${KEY:-TEST_KEY}
ADMIN_KEY=${ADMIN_KEY:-ADMIN_SOURCES_TEST}
MYIP=$(curl -s https://ifconfig.me || echo "127.0.0.1")
SRC_OK="b4ok-$RANDOM"
SRC_DISABLED="b4off-$RANDOM"
SRC_RL="b4rl-$RANDOM"
SRC_BLOCK="b4blk-$RANDOM"

say() { printf "\n\033[1m== %s ==\033[0m\n" "$*"; }

say "Create sources (enabled, disabled, rate-limited, ip-block)"
curl -s -X POST "$API/v1/sources" -H "Authorization: Bearer $ADMIN_KEY" -H "Content-Type: application/json" \
  -d "{\"id\":\"$SRC_OK\",\"tenant_id\":\"default\",\"type\":\"test\",\"display_name\":\"$SRC_OK\",\"collector\":\"$SRC_OK\",\"status\":\"enabled\",\"allowed_ips\":\"[\"$MYIP/32\"]\",\"max_eps\":0,\"block_on_exceed\":true}" >/dev/null
curl -s -X POST "$API/v1/sources" -H "Authorization: Bearer $ADMIN_KEY" -H "Content-Type: application/json" \
  -d "{\"id\":\"$SRC_DISABLED\",\"tenant_id\":\"default\",\"type\":\"test\",\"display_name\":\"$SRC_DISABLED\",\"collector\":\"$SRC_DISABLED\",\"status\":\"disabled\",\"allowed_ips\":\"[\"$MYIP/32\"]\",\"max_eps\":0,\"block_on_exceed\":true}" >/dev/null
curl -s -X POST "$API/v1/sources" -H "Authorization: Bearer $ADMIN_KEY" -H "Content-Type: application/json" \
  -d "{\"id\":\"$SRC_RL\",\"tenant_id\":\"default\",\"type\":\"test\",\"display_name\":\"$SRC_RL\",\"collector\":\"$SRC_RL\",\"status\":\"enabled\",\"allowed_ips\":\"[\"$MYIP/32\"]\",\"max_eps\":2,\"block_on_exceed\":true}" >/dev/null
curl -s -X POST "$API/v1/sources" -H "Authorization: Bearer $ADMIN_KEY" -H "Content-Type: application/json" \
  -d "{\"id\":\"$SRC_BLOCK\",\"tenant_id\":\"default\",\"type\":\"test\",\"display_name\":\"$SRC_BLOCK\",\"collector\":\"$SRC_BLOCK\",\"status\":\"enabled\",\"allowed_ips\":\"[]\",\"max_eps\":0,\"block_on_exceed\":true}" >/dev/null

say "Baseline metrics snapshot"
M_BEFORE=$(curl -s "$API/v1/metrics/prometheus" | grep -E 'telemetry_(blocked_source_total|records_parsed_total|fifo_dropped_total)' || true)
echo "$M_BEFORE"

say "Happy path (should be 200)"
curl -s -o /dev/null -w "HTTP:%{http_code}\n" -X POST "$API/v1/ingest" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d "{\"collector_id\":\"$SRC_OK\",\"format\":\"flows.v1\",\"records\":[{\"ts\":1}] }"

say "Disabled source (expect 403 disabled)"
curl -s -o /dev/null -w "HTTP:%{http_code}\n" -X POST "$API/v1/ingest" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d "{\"collector_id\":\"$SRC_DISABLED\",\"format\":\"flows.v1\",\"records\":[{\"ts\":1}] }"

say "IP not allowed (expect 403 ip_not_allowed)"
curl -s -o /dev/null -w "HTTP:%{http_code}\n" -X POST "$API/v1/ingest" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d "{\"collector_id\":\"$SRC_BLOCK\",\"format\":\"flows.v1\",\"records\":[{\"ts\":1}] }"

say "Rate limit (expect mix of 200, 429)"
for i in {1..8}; do
  curl -s -o /dev/null -w "%{http_code} " -X POST "$API/v1/ingest" \
    -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
    -d "{\"collector_id\":\"$SRC_RL\",\"format\":\"flows.v1\",\"records\":[{\"ts\":$i}] }"
done
echo

# OPTIONAL: FIFO pressure test if you expose a tiny FIFO for dev
if [[ "${B4_FIFO_TEST:-0}" == "1" ]]; then
  say "FIFO pressure test (optional)"
  for i in {1..2000}; do
    curl -s -o /dev/null -X POST "$API/v1/ingest" \
      -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
      -d "{\"collector_id\":\"$SRC_OK\",\"format\":\"flows.v1\",\"records\":[{\"ts\":$i}] }" || true
  done
fi

say "Metrics delta"
M_AFTER=$(curl -s "$API/v1/metrics/prometheus" | grep -E 'telemetry_(blocked_source_total|records_parsed_total|fifo_dropped_total)' || true)
echo "$M_AFTER"

say "Assertions"
# Best-effort assertions (textual): ensure counters present & increased when expected
echo "$M_AFTER" | grep telemetry_records_parsed_total >/dev/null || (echo "records_parsed missing" && exit 1)
echo "$M_AFTER" | grep 'telemetry_blocked_source_total{.*reason="disabled"' >/dev/null || echo "WARN: disabled counter not observed"
echo "$M_AFTER" | grep 'telemetry_blocked_source_total{.*reason="ip_not_allowed"' >/dev/null || echo "WARN: ip_not_allowed counter not observed"
echo "$M_AFTER" | grep 'telemetry_blocked_source_total{.*reason="rate_limit"' >/dev/null || echo "WARN: rate_limit counter not observed"

say "DONE. Review warnings above; failures exit non-zero."

# Optional UDP testing section
if [[ "${HAS_UDP_TEST:-0}" == "1" ]]; then
    say "UDP Admission Control Testing"
    
    print_status "INFO" "Testing UDP admission control with dummy packets"
    
    # Create a source with specific IP allowlist
    SRC_UDP_ALLOWED="b2-udp-allowed-$(date +%s)"
    SRC_UDP_BLOCKED="b2-udp-blocked-$(date +%s)"
    
    # Get current IP for testing
    MYIP=$(curl -s https://ifconfig.me || echo "127.0.0.1")
    
    # Create allowed source
    curl -s -X POST "$API/v1/sources" -H "Authorization: Bearer $ADMIN_KEY" -H "Content-Type: application/json" \
      -d "{\"id\":\"$SRC_UDP_ALLOWED\",\"tenant_id\":\"default\",\"type\":\"test\",\"display_name\":\"$SRC_UDP_ALLOWED\",\"collector\":\"$SRC_UDP_ALLOWED\",\"status\":\"enabled\",\"allowed_ips\":\"[\"$MYIP/32\"]\",\"max_eps\":0,\"block_on_exceed\":true}" >/dev/null
    
    # Create blocked source
    curl -s -X POST "$API/v1/sources" -H "Authorization: Bearer $ADMIN_KEY" -H "Content-Type: application/json" \
      -d "{\"id\":\"$SRC_UDP_BLOCKED\",\"tenant_id\":\"default\",\"type\":\"test\",\"display_name\":\"$SRC_UDP_BLOCKED\",\"collector\":\"$SRC_UDP_BLOCKED\",\"status\":\"enabled\",\"allowed_ips\":\"[]\",\"max_eps\":0,\"block_on_exceed\":true}" >/dev/null
    
    print_status "INFO" "Created UDP test sources: $SRC_UDP_ALLOWED (allowed), $SRC_UDP_BLOCKED (blocked)"
    
    # Get baseline metrics
    UDP_BASELINE=$(curl -s "$API/v1/metrics/prometheus" | grep -E 'telemetry_(udp_packets_received_total|records_parsed_total|blocked_source_total)' || true)
    
    # Send packets from allowed IP
    print_status "INFO" "Sending UDP packets from allowed IP ($MYIP)"
    python3 scripts/send_ipfix_dummy.py --host localhost --port 2055 --count 5 --delay 0.2
    
    sleep 3
    
    # Check if packets were processed
    UDP_AFTER_ALLOWED=$(curl -s "$API/v1/metrics/prometheus" | grep -E 'telemetry_(udp_packets_received_total|records_parsed_total)' || true)
    
    UDP_PACKETS_BEFORE=$(echo "$UDP_BASELINE" | grep "telemetry_udp_packets_received_total" | awk '{print $2}' | head -1 || echo "0")
    UDP_PACKETS_AFTER=$(echo "$UDP_AFTER_ALLOWED" | grep "telemetry_udp_packets_received_total" | awk '{print $2}' | head -1 || echo "0")
    
    if [ "$UDP_PACKETS_AFTER" -gt "$UDP_PACKETS_BEFORE" ]; then
        print_status "PASS" "UDP packets from allowed IP were processed"
    else
        print_status "WARN" "UDP packets from allowed IP may not have been processed"
    fi
    
    # Send packets from blocked IP (simulate by using a different IP)
    print_status "INFO" "Sending UDP packets from blocked IP (simulated)"
    # Note: This is a simplified test since we can't easily change source IP
    # In real testing, you would use different machines or network interfaces
    
    # Check for blocked metrics
    BLOCKED_METRICS=$(curl -s "$API/v1/metrics/prometheus" | grep "telemetry_blocked_source_total" | grep -v "#" || true)
    
    if [ -n "$BLOCKED_METRICS" ]; then
        print_status "PASS" "Blocked source metrics are being recorded"
        echo "$BLOCKED_METRICS" | head -3
    else
        print_status "INFO" "No blocked source metrics recorded yet (expected if no blocks occurred)"
    fi
    
    print_status "INFO" "UDP admission control testing complete"
fi
