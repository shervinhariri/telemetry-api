#!/bin/bash

echo "=== UDP HEAD FEATURE TEST ==="
echo ""

API_KEY="DEV_ADMIN_KEY_5a8f9ffdc3"
BASE_URL="http://localhost:8080"

echo "1. Testing UDP Head status:"
echo "   System endpoint:"
curl -s -H "Authorization: Bearer $API_KEY" $BASE_URL/v1/system | jq '.udp_head'

echo ""
echo "2. Testing UDP Head metrics (before):"
echo "   Metrics endpoint:"
curl -s -H "Authorization: Bearer $API_KEY" $BASE_URL/v1/metrics | jq '.udp_head_packets_total, .udp_head_bytes_total, .udp_head_last_packet_ts'

echo ""
echo "3. Sending UDP packet:"
echo "   Using Python to send UDP packet..."
python3 -c "
import socket
import time

# Send multiple packets
for i in range(3):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data = f'test packet {i}'.encode()
    s.sendto(data, ('localhost', 8081))
    print(f'Sent packet {i}: {len(data)} bytes')
    s.close()
    time.sleep(0.1)
"

echo ""
echo "4. Waiting for processing..."
sleep 3

echo ""
echo "5. Testing UDP Head metrics (after):"
echo "   Metrics endpoint:"
curl -s -H "Authorization: Bearer $API_KEY" $BASE_URL/v1/metrics | jq '.udp_head_packets_total, .udp_head_bytes_total, .udp_head_last_packet_ts'

echo ""
echo "6. Checking container logs for UDP activity:"
echo "   Recent logs:"
docker logs telemetry-api-dev | grep -i "udp\|datagram\|packet" | tail -5

echo ""
echo "=== TEST COMPLETE ==="
