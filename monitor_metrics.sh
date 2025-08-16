#!/bin/bash

echo "🔍 Monitoring Telemetry API Metrics"
echo "=================================="
echo "Press Ctrl+C to stop"
echo ""

while true; do
    echo "$(date '+%H:%M:%S') - Fetching metrics..."
    
    # Get metrics
    METRICS=$(curl -s -H "Authorization: Bearer TEST_KEY" http://localhost:8080/v1/metrics)
    
    # Extract key values
    RECORDS=$(echo $METRICS | jq -r '.records_processed')
    EVENTS=$(echo $METRICS | jq -r '.totals.events')
    RISK_COUNT=$(echo $METRICS | jq -r '.totals.risk_count')
    RISK_SUM=$(echo $METRICS | jq -r '.totals.risk_sum')
    THREAT_MATCHES=$(echo $METRICS | jq -r '.totals.threat_matches')
    
    # Calculate average risk
    if [ "$RISK_COUNT" -gt 0 ]; then
        AVG_RISK=$(echo "scale=1; $RISK_SUM / $RISK_COUNT" | bc)
    else
        AVG_RISK="0.0"
    fi
    
    echo "📊 Records: $RECORDS | Events: $EVENTS | Avg Risk: $AVG_RISK | Threats: $THREAT_MATCHES"
    
    sleep 2
done
