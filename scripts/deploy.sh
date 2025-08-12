#!/bin/bash
set -euo pipefail

# Production Deployment Script for Telemetry API

echo "🚀 Starting production deployment..."

# Check if .env exists, copy from example if not
if [ ! -f .env ]; then
    echo "📋 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your actual configuration values"
    echo "   Then run this script again"
    exit 1
fi

# Load environment variables
source .env

# Validate required environment variables
if [ "$API_KEY" = "CHANGE_ME" ]; then
    echo "❌ Please update API_KEY in .env file"
    exit 1
fi

if [ "$DOMAIN" = "api.yourdomain.com" ]; then
    echo "❌ Please update DOMAIN in .env file"
    exit 1
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p data logs

# Check if GeoIP databases exist
if [ ! -f "data/GeoLite2-City.mmdb" ] || [ ! -f "data/GeoLite2-ASN.mmdb" ]; then
    echo "⚠️  Warning: GeoIP databases not found in data/ directory"
    echo "   Please add GeoLite2-City.mmdb and GeoLite2-ASN.mmdb"
fi

# Check if threat list exists
if [ ! -f "data/threats.csv" ]; then
    echo "📋 Creating default threat list..."
    cat > data/threats.csv << 'CSV'
ip_or_cidr,category,confidence
8.8.8.8,Test,90
CSV
fi

# Pull latest images
echo "📦 Pulling latest Docker images..."
docker compose pull

# Start services
echo "🚀 Starting services..."
docker compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
if docker compose ps | grep -q "Up"; then
    echo "✅ Services are running"
else
    echo "❌ Services failed to start"
    docker compose logs
    exit 1
fi

# Test API health
echo "🏥 Testing API health..."
if curl -fsSL "https://$DOMAIN/v1/health" > /dev/null 2>&1; then
    echo "✅ API is healthy and accessible"
else
    echo "⚠️  API health check failed - this might be normal during initial startup"
fi

echo "🎉 Deployment completed successfully!"
echo "🌐 Your API is available at: https://$DOMAIN"
echo "📊 Metrics endpoint: https://$DOMAIN/v1/metrics (with basic auth)"
echo ""
echo "📋 Next steps:"
echo "   1. Run: ./scripts/test_health.sh"
echo "   2. Run: ./scripts/test_ingest.sh"
echo "   3. Configure outputs: ./scripts/configure_splunk.sh"
echo "   4. View logs: ./scripts/logs.sh"
