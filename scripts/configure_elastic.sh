#!/bin/bash
set -euo pipefail

# Elasticsearch Configuration Script for Telemetry API

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo "❌ .env file not found"
    exit 1
fi

echo "🔧 Configuring Elasticsearch output..."

# Validate Elasticsearch configuration
if [ "$ELASTIC_URL" = "https://elastic.example.com:9200" ]; then
    echo "❌ Please update ELASTIC_URL in .env file"
    exit 1
fi

if [ "$ELASTIC_USERNAME" = "elastic" ] && [ "$ELASTIC_PASSWORD" = "changeme" ]; then
    echo "❌ Please update ELASTIC_USERNAME and ELASTIC_PASSWORD in .env file"
    exit 1
fi

# Configure Elasticsearch output
echo "📊 Configuring Elasticsearch..."
response=$(curl -s -X POST "https://$DOMAIN/v1/outputs/elastic" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"url\":\"$ELASTIC_URL\",\"username\":\"$ELASTIC_USERNAME\",\"password\":\"$ELASTIC_PASSWORD\"}" 2>/dev/null || echo "FAILED")

if [ "$response" = "FAILED" ]; then
    echo "❌ Elasticsearch configuration failed"
    echo "   Make sure:"
    echo "   1. API is running and accessible"
    echo "   2. Elasticsearch URL and credentials are correct"
    echo "   3. Check logs: ./scripts/logs.sh"
    exit 1
fi

echo "✅ Elasticsearch configured successfully"
echo "📊 Response:"
echo "$response" | jq .

echo ""
echo "🎯 Next steps:"
echo "   1. Send test data: ./scripts/test_ingest.sh"
echo "   2. Check Elasticsearch for incoming data"
echo "   3. Configure Splunk: ./scripts/configure_splunk.sh"
