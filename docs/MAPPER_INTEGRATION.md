# NetFlow Mapper Integration

The NetFlow mapper service reads goflow2 JSON output and maps it to flows.v1 format, then batches and posts it to the telemetry API's `/v1/ingest` endpoint.

## Overview

The mapper service (`ops/mapper/nf2ingest.py`) provides:

- **Field Mapping**: Converts goflow2 NetFlow fields to flows.v1 format
- **Batching**: Groups records into configurable batches (default: 200)
- **Retry Logic**: Handles 429/5xx errors with exponential backoff
- **Payload Optimization**: Gzips payloads >50KB, respects 5MB limit
- **Authentication**: Uses Bearer token authentication

## Architecture

```
NetFlow Sources → Collector (goflow2) → Mapper → Telemetry API
     ↓              ↓                    ↓           ↓
  UDP/2055    JSON Lines (STDOUT)   flows.v1    /v1/ingest
```

## Field Mapping

The mapper converts goflow2 fields to flows.v1 format:

| goflow2 Field | flows.v1 Field | Notes |
|---------------|----------------|-------|
| `time_flow_start_ns` | `ts` | Converted from nanoseconds to seconds |
| `src_addr` | `src_ip` | Source IP address |
| `dst_addr` | `dst_ip` | Destination IP address |
| `src_port` | `src_port` | Source port |
| `dst_port` | `dst_port` | Destination port |
| `proto` | `proto` | Protocol (mapped to numeric values) |
| `bytes` | `bytes` | Bytes transferred |
| `packets` | `packets` | Packets transferred |
| `in_if` | `ingress_if` | Optional ingress interface |
| `out_if` | `egress_if` | Optional egress interface |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API` | `http://telemetry-api:8080` | Telemetry API base URL |
| `KEY` | `TEST_KEY` | Bearer token for authentication |
| `COLLECTOR_ID` | `gw-local` | Collector identifier |
| `BATCH_SIZE` | `200` | Records per batch |
| `FLUSH_INTERVAL` | `1` | Flush interval in seconds |
| `MAX_RECORDS_PER_BATCH` | `10000` | Maximum records per batch |
| `MAX_PAYLOAD_SIZE` | `5242880` | Maximum payload size (5MB) |
| `GZIP_THRESHOLD` | `51200` | Gzip threshold (50KB) |

### Docker Compose Service

```yaml
mapper:
  build: ./ops/mapper
  environment:
    - API=http://api:80
    - KEY=TEST_KEY
    - COLLECTOR_ID=gw-local
    - BATCH_SIZE=200
    - FLUSH_INTERVAL=1
  depends_on:
    - api
  restart: unless-stopped
```

## Usage

### Manual Integration

For development and testing, run the mapper manually with collector logs:

```bash
# Start services
docker compose up -d api collector

# Run mapper with collector logs
docker compose logs -f collector | grep "NETFLOW_V" | sed 's/.*| //' | \
  docker compose run --rm -T mapper python3 nf2ingest.py
```

### Automated Testing

Use the provided verification script:

```bash
# Run complete verification test
./scripts/verify_mapper.sh
```

### Production Integration

For production, consider:

1. **Named Pipes**: Create a named pipe between collector and mapper
2. **Message Queue**: Use Redis, RabbitMQ, or Kafka for reliable delivery
3. **File-based**: Write collector output to files, mapper reads files
4. **Direct Integration**: Modify goflow2 to output directly to API

## Testing

### Generate Test Data

```bash
# Generate NetFlow test packets
python3 scripts/generate_test_netflow.py --count 10 --flows 3
```

### Verify Integration

```bash
# Check API metrics
curl -s -H "Authorization: Bearer TEST_KEY" \
  "http://localhost/v1/metrics?window=300" | jq

# Expected output:
# {
#   "requests_total": 123,
#   "records_processed": 456,
#   "eps": 78
# }
```

### Monitor Logs

```bash
# Watch mapper logs
docker compose logs -f mapper

# Watch collector logs
docker compose logs -f collector | grep "NETFLOW_V"
```

## Error Handling

### Retry Logic

The mapper implements exponential backoff for:
- HTTP 429 (Rate Limited)
- HTTP 5xx (Server Errors)
- Network timeouts

### Batch Splitting

On HTTP 413 (Payload Too Large):
- Automatically splits batch in half
- Retries with smaller batch
- Continues until successful

### Logging

Mapper logs include:
- `[INGEST] sent N status=200` - Successful batches
- `[INGEST][ERR] HTTP XXX` - HTTP errors
- `[INGEST][ERR] Request failed` - Network errors

## Performance Considerations

### Batch Optimization

- **Small batches** (50-200): Lower latency, higher overhead
- **Large batches** (500-1000): Higher throughput, higher memory usage
- **Optimal**: 200-500 records per batch

### Memory Usage

- Each batch held in memory until sent
- Monitor memory usage with large batch sizes
- Consider reducing batch size if memory constrained

### Network Optimization

- Gzip compression for payloads >50KB
- Connection pooling via requests session
- Configurable timeouts (default: 30s)

## Troubleshooting

### Common Issues

1. **No records processed**
   - Check collector is receiving NetFlow data
   - Verify mapper can connect to API
   - Check authentication token

2. **High error rates**
   - Reduce batch size
   - Check API rate limits
   - Verify network connectivity

3. **Memory issues**
   - Reduce batch size
   - Increase flush interval
   - Monitor container memory usage

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
docker compose run --rm mapper python3 nf2ingest.py
```

### Health Checks

```bash
# Check API connectivity
curl -H "Authorization: Bearer TEST_KEY" http://localhost/v1/health

# Check collector status
docker compose logs collector | grep "starting collection"

# Check mapper status
docker compose logs mapper | grep "Starting NetFlow mapper"
```

## Integration Examples

### With Network Devices

```bash
# Configure router to send NetFlow to collector
# Router config example (Cisco):
# ip flow-export destination 192.168.1.100 2055
# ip flow-export version 5

# Start services
docker compose up -d api collector

# Run mapper
docker compose logs -f collector | grep "NETFLOW_V" | sed 's/.*| //' | \
  docker compose run --rm -T mapper python3 nf2ingest.py
```

### With softflowd (Linux)

```bash
# Install softflowd
sudo apt-get install -y softflowd

# Start softflowd
sudo softflowd -i eth0 -n 127.0.0.1:2055 -v 9 -t maxlife=60

# Start services and mapper
docker compose up -d api collector
docker compose logs -f collector | grep "NETFLOW_V" | sed 's/.*| //' | \
  docker compose run --rm -T mapper python3 nf2ingest.py
```

## Security Considerations

- **Authentication**: Always use secure API keys
- **Network**: Restrict access to collector port (UDP/2055)
- **Logging**: Avoid logging sensitive data
- **Monitoring**: Monitor for unusual traffic patterns
