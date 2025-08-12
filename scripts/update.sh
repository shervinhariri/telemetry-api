#!/bin/bash
set -euo pipefail

# Update Script for Telemetry API

echo "🔄 Updating Telemetry API..."

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo "❌ .env file not found"
    exit 1
fi

# Pull latest API image
echo "📦 Pulling latest API image..."
docker compose pull api

# Update API service
echo "🚀 Updating API service..."
docker compose up -d api

# Wait for service to be healthy
echo "⏳ Waiting for API to be healthy..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
if docker compose ps api | grep -q "Up"; then
    echo "✅ API updated successfully"
else
    echo "❌ API update failed"
    docker compose logs api
    exit 1
fi

echo "🎉 Update completed successfully!"
echo "📊 API is running with latest image: $API_IMAGE"
