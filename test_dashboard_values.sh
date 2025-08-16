#!/bin/bash

echo "🎯 DASHBOARD VALUES TEST"
echo "========================"

# Get current metrics
METRICS=$(curl -s -H "Authorization: Bearer TEST_KEY" http://localhost:8080/v1/metrics)

echo ""
echo "📊 Current Metrics:"
echo "Queue Depth: $(echo $METRICS | jq -r '.queue_depth')"
echo "Risk Sum: $(echo $METRICS | jq -r '.totals.risk_sum')"
echo "Risk Count: $(echo $METRICS | jq -r '.totals.risk_count')"
echo "Threat Matches: $(echo $METRICS | jq -r '.totals.threat_matches')"
echo "Requests Total: $(echo $METRICS | jq -r '.requests_total')"
echo "Requests Failed: $(echo $METRICS | jq -r '.requests_failed')"

echo ""
echo "🔧 Expected Dashboard Values:"
echo "Queue Lag: $(echo $METRICS | jq -r '.queue_depth')"
echo "Avg Risk: $(echo $METRICS | jq -r 'if .totals.risk_count > 0 then (.totals.risk_sum / .totals.risk_count) else 0 end | . * 10 | floor / 10')"
echo "Threat Matches: $(echo $METRICS | jq -r '.totals.threat_matches')"
echo "Error Rate: $(echo $METRICS | jq -r 'if .requests_total > 0 then (.requests_failed / .requests_total * 100) else 0 end | . * 10 | floor / 10')%"

echo ""
echo "✅ Expected Results:"
echo "Queue Lag (records): Should show $(echo $METRICS | jq -r '.queue_depth')"
echo "Avg Risk (0-10): Should show $(echo $METRICS | jq -r 'if .totals.risk_count > 0 then (.totals.risk_sum / .totals.risk_count) else 0 end | . * 10 | floor / 10')"
echo "Threat Matches (15m): Should show $(echo $METRICS | jq -r '.totals.threat_matches')"
echo "Error Rate (%): Should show $(echo $METRICS | jq -r 'if .requests_total > 0 then (.requests_failed / .requests_total * 100) else 0 end | . * 10 | floor / 10')%"

echo ""
echo "🎯 Next: Open http://localhost:8080 and hard refresh (Ctrl+Shift+R)"
echo "Check console for logs starting with 🔧 and ✅"

