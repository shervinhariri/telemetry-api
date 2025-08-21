# Logging & Observability

## Overview

The Telemetry API uses structured JSON logging with request tracing, correlation IDs, and comprehensive observability features.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_FORMAT` | `json` | Log format: `json` or `text` |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_SAMPLE_RATE` | `1.0` | Request sampling rate (0.0-1.0) |
| `LOG_EXCLUDE_PATHS` | `/v1/health,/v1/metrics/prometheus` | Paths to exclude from request logging |

### Configuration File

The system loads logging configuration from `LOGGING.yaml` at startup:

```yaml
version: 1
disable_existing_loggers: false

formatters:
  json:
    class: app.logging_config.JsonFormatter
  text:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: json
    stream: ext://sys.stdout
  
  memory:
    class: app.logging_config.MemoryLogHandler
    level: INFO
    formatter: json
    max_size: 10000
```

## JSON Log Schema

All logs follow a consistent JSON structure:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "app",
  "msg": "HTTP Request",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/v1/ingest",
  "status": 200,
  "latency_ms": 45.2,
  "client_ip": "192.168.1.100",
  "tenant_id": "default",
  "component": "api"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 timestamp in UTC |
| `level` | string | Log level (DEBUG, INFO, WARNING, ERROR) |
| `logger` | string | Logger name |
| `msg` | string | Log message |
| `trace_id` | string | Request correlation ID |
| `method` | string | HTTP method (for requests) |
| `path` | string | Request path (for requests) |
| `status` | integer | HTTP status code (for requests) |
| `latency_ms` | float | Request latency in milliseconds |
| `client_ip` | string | Client IP address |
| `tenant_id` | string | Tenant identifier |
| `component` | string | Component name (api, mapper, etc.) |

## Request Tracing

### Trace ID Generation

- **Inbound requests**: Reuse `X-Request-ID` header if present
- **Generated requests**: Create new UUID4 trace ID
- **Mapper requests**: Generate trace ID and propagate to API

### Correlation

The mapper service generates trace IDs and includes them in requests to the API:

```python
# Mapper generates trace ID
trace_id = str(uuid.uuid4())
headers = {
    "X-Request-ID": trace_id,
    "Authorization": f"Bearer {API_KEY}"
}
```

Both mapper and API logs will show the same `trace_id` for correlated operations.

## Live Logs API

### Get Logs

```bash
# Get recent logs
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost/v1/logs?limit=100"

# Filter by level
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost/v1/logs?level=ERROR"

# Filter by trace ID
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost/v1/logs?trace_id=550e8400-e29b-41d4-a716-446655440000"

# Filter by endpoint
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost/v1/logs?endpoint=/v1/ingest"
```

### Stream Logs (SSE)

```bash
# Stream live logs
curl -N -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost/v1/logs/stream"
```

### Download Logs

```bash
# Download as JSON lines
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost/v1/logs/download?limit=1000" \
  -o telemetry-logs.jsonl
```

## Metrics Integration

### Success Rate

The system tracks request success rates:

```json
{
  "requests_total": 1500,
  "requests_success": 1485,
  "requests_failed": 15,
  "requests_last_15m_success_rate": 99.0
}
```

### Latency Tracking

Average latency is calculated from recent requests:

```json
{
  "latency_ms_avg": 45.2
}
```

## Examples

### HTTP Request Log

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "app",
  "msg": "HTTP Request",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/v1/ingest",
  "status": 200,
  "latency_ms": 45.2,
  "client_ip": "192.168.1.100",
  "tenant_id": "default",
  "component": "api"
}
```

### Error Log

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "ERROR",
  "logger": "app",
  "msg": "Request failed: Invalid API key",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/v1/ingest",
  "status": 401,
  "latency_ms": 12.5,
  "client_ip": "192.168.1.100",
  "tenant_id": "unknown",
  "component": "api",
  "exception": "Invalid API key"
}
```

### Mapper Log

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "mapper",
  "msg": "Mapper sending batch with trace_id: 550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "component": "mapper"
}
```

## Troubleshooting

### Common Issues

1. **No logs appearing**: Check `LOG_LEVEL` and `LOG_SAMPLE_RATE`
2. **Missing trace IDs**: Ensure `X-Request-ID` headers are being set
3. **High latency**: Monitor `latency_ms` field in logs
4. **Memory usage**: Adjust `max_size` in MemoryLogHandler

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
export LOG_SAMPLE_RATE=1.0
```

### Log Analysis

Use `jq` to analyze logs:

```bash
# Count by level
docker logs telemetry-api-api-1 | jq -r '.level' | sort | uniq -c

# Find slow requests
docker logs telemetry-api-api-1 | jq -r 'select(.latency_ms > 100) | {path, latency_ms, trace_id}'

# Track specific trace ID
docker logs telemetry-api-api-1 | jq -r 'select(.trace_id == "550e8400-e29b-41d4-a716-446655440000")'
```
