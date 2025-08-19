#!/bin/bash
set -euo pipefail

# NetFlow Collector Test Script
# Tests the goflow2 collector service with sample NetFlow data

echo "🧪 Testing NetFlow Collector"
echo "============================"

# Check if collector is running
if ! docker compose ps collector | grep -q "Up"; then
    echo "❌ Collector service is not running. Start it with:"
    echo "   docker compose up -d collector"
    exit 1
fi

echo "✅ Collector service is running"
echo ""

# Show collector logs
echo "📋 Collector logs (last 10 lines):"
docker compose logs --tail=10 collector
echo ""

# Instructions for testing
echo "🔍 To monitor collector logs in real-time:"
echo "   docker compose logs -f collector"
echo ""
echo "📡 To send test NetFlow data:"
echo "   # Using the included Python generator:"
echo "   python3 scripts/generate_test_netflow.py --count 5 --flows 3"
echo ""
echo "   # Using nflowgen (if available):"
echo "   nflowgen -r 1 -i 127.0.0.1:2055"
echo ""
echo "   # Using netflow-generator (if available):"
echo "   netflow-generator -h 127.0.0.1 -p 2055 -r 1"
echo ""
echo "   # Using custom tools or network devices"
echo ""

# Check if we can see any flow records
echo "📊 Checking for recent flow records..."
RECENT_FLOWS=$(docker compose logs collector 2>/dev/null | grep -c "flow" || echo "0")
echo "   Recent flow records found: $RECENT_FLOWS"
echo ""

echo "✅ NetFlow collector is ready for testing!"
echo "   UDP Port: 2055"
echo "   Format: JSON (line-delimited)"
echo "   Output: STDOUT (viewable via docker logs)"
