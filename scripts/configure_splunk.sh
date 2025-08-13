#!/bin/bash
set -euo pipefail

# Splunk HEC Configuration Script for Telemetry API

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo "❌ .env file not found"
    exit 1
fi

echo "🔧 Configuring Splunk HEC output..."

# Validate Splunk configuration
if [ "$SPLUNK_HEC_URL" = "https://splunk.example.com:8088/services/collector" ]; then
    echo "❌ Please update SPLUNK_HEC_URL in .env file"
    exit 1
fi

if [ "$SPLUNK_HEC_TOKEN" = "changeme" ]; then
    echo "❌ Please update SPLUNK_HEC_TOKEN in .env file"
    exit 1
fi

# Configure Splunk HEC output
echo "📊 Configuring Splunk HEC..."
response=$(curl -s -X POST "https://$DOMAIN/v1/outputs/splunk" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"hec_url\":\"$SPLUNK_HEC_URL\",\"token\":\"$SPLUNK_HEC_TOKEN\"}" 2>/dev/null || echo "FAILED")

if [ "$response" = "FAILED" ]; then
    echo "❌ Splunk configuration failed"
    echo "   Make sure:"
    echo "   1. API is running and accessible"
    echo "   2. Splunk HEC URL and token are correct"
    echo "   3. Check logs: ./scripts/logs.sh"
    exit 1
fi

echo "✅ Splunk HEC configured successfully"
echo "📊 Response:"
echo "$response" | jq .

echo ""
echo "🎯 Next steps:"
echo "   1. Send test data: ./scripts/test_ingest.sh"
echo "   2. Check Splunk for incoming data"
echo "   3. Configure Elasticsearch: ./scripts/configure_elastic.sh"
