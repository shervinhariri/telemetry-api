# Telemetry API Logging Configuration

This document describes the structured logging system and request audit capabilities of the Telemetry API.

## Overview

The Telemetry API uses a professional, scalable logging approach that:
- **Reduces noise** through sampling and filtering
- **Maintains signal** by always logging errors and important events
- **Provides structured data** in JSON format for easy parsing
- **Includes request timelines** for debugging and monitoring

## Environment Variables

### Core Logging
- `LOG_LEVEL`: Log level (INFO, WARNING, ERROR) - default: INFO
- `LOG_FORMAT`: Output format (json, text) - default: json
- `ENVIRONMENT`: Environment (development, production) - default: production

### HTTP Request Logging
- `HTTP_LOG_ENABLED`: Enable/disable HTTP request logging (true/false) - default: true
- `HTTP_LOG_SAMPLE_RATE`: Sample rate for 2xx responses (0.0-1.0) - default: 0.01 (1%)
- `HTTP_LOG_EXCLUDE_PATHS`: Comma-separated paths to exclude from logging - default: `/v1/metrics,/v1/system,/v1/logs/tail,/v1/admin/requests`
- `REDACT_HEADERS`: Comma-separated headers to redact - default: `authorization,x-api-key`

## Request Audit System

The API maintains a ring buffer of request audits with timeline events for each request.

### Timeline Events

Each request generates up to 5 timeline events:

1. **received** - Request received
   ```json
   {
     "ts": "2025-08-17T21:10:30.076457+00:00",
     "event": "received",
     "meta": {
       "tenant": "tenant_489",
       "auth": "ingest"
     }
   }
   ```

2. **validated** - Schema validation (for ingest requests)
   ```json
   {
     "ts": "2025-08-17T21:10:30.077557+00:00",
     "event": "validated",
     "meta": {
       "schema": "flows.v1",
       "ok": true,
       "records": 1
     }
   }
   ```

3. **enriched** - Data enrichment (for ingest requests)
   ```json
   {
     "ts": "2025-08-17T21:10:30.077624+00:00",
     "event": "enriched",
     "meta": {
       "geo": 1,
       "asn": 1,
       "ti": 0,
       "risk_avg": 18.7
     }
   }
   ```

4. **exported** - Data export (for ingest requests)
   ```json
   {
     "ts": "2025-08-17T21:10:30.077633+00:00",
     "event": "exported",
     "meta": {
       "splunk": "ok",
       "elastic": "ok",
       "count": 1
     }
   }
   ```

5. **completed** - Request completed
   ```json
   {
     "ts": "2025-08-17T21:10:30.079173+00:00",
     "event": "completed",
     "meta": {
       "status": 200,
       "latency_ms": 2.8
     }
   }
   ```

### Audit API Endpoints

- `GET /v1/admin/requests` - Get recent request audits with timeline
- `GET /v1/admin/requests/summary` - Get audit summary statistics
- `GET /v1/api/requests` - Legacy endpoint for UI compatibility

### Audit Data Structure

```json
{
  "id": "trace-id-uuid",
  "ts": "2025-08-17T21:10:30.076434+00:00",
  "method": "POST",
  "path": "/v1/ingest",
  "client_ip": "192.168.65.1",
  "tenant_id": "tenant_489",
  "status": 200,
  "latency_ms": 2.8123855590820312,
  "summary": {},
  "timeline": [
    // Timeline events as shown above
  ]
}
```

## Log Formats

### JSON Format (Production)
```json
{
  "ts": "2025-08-17T21:10:30.076434+00:00",
  "level": "INFO",
  "msg": "http_request",
  "trace_id": "trace-id-uuid",
  "method": "POST",
  "path": "/v1/ingest",
  "status": 200,
  "latency_ms": 2.8,
  "client_ip": "192.168.65.1",
  "tenant_id": "tenant_489"
}
```

### Text Format (Development)
```
2025-08-17T21:10:30.076434 | INFO | 🌐 HTTP REQUEST
2025-08-17T21:10:30.076434 | INFO | ✅ POST /v1/ingest → 200
2025-08-17T21:10:30.076434 | INFO | 🟢 Duration: 3ms
2025-08-17T21:10:30.076434 | INFO | 📍 Client: 192.168.65.1
2025-08-17T21:10:30.076434 | INFO | 🔍 Trace ID: trace-id-uuid
```

## Sampling Strategy

- **Always log**: 4xx and 5xx responses (errors)
- **Sample**: 2xx responses based on `HTTP_LOG_SAMPLE_RATE`
- **Exclude**: Noisy endpoints like metrics, health checks, and admin endpoints
- **Queue-based**: Non-blocking logging using QueueHandler/QueueListener

## Configuration Examples

### Development
```bash
export LOG_LEVEL=INFO
export LOG_FORMAT=text
export ENVIRONMENT=development
export HTTP_LOG_SAMPLE_RATE=0.1  # 10% sampling
```

### Production
```bash
export LOG_LEVEL=WARNING
export LOG_FORMAT=json
export ENVIRONMENT=production
export HTTP_LOG_SAMPLE_RATE=0.01  # 1% sampling
export HTTP_LOG_EXCLUDE_PATHS=/v1/metrics,/v1/system,/v1/logs/tail,/v1/admin/requests
```

## Docker Compose Configuration

### Production Override
```yaml
# docker-compose.prod.yml
services:
  api:
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=WARNING
      - LOG_FORMAT=json
      - HTTP_LOG_ENABLED=true
      - HTTP_LOG_SAMPLE_RATE=0.01
      - HTTP_LOG_EXCLUDE_PATHS=/v1/metrics,/v1/system,/v1/logs/tail,/v1/admin/requests
      - REDACT_HEADERS=authorization,x-api-key
      - DEMO_MODE=false
```

## Benefits

1. **Reduced Noise**: Only 1% of successful requests are logged
2. **Structured Data**: JSON format for easy parsing and analysis
3. **Request Tracing**: Full timeline for debugging and monitoring
4. **Performance**: Non-blocking queue-based logging
5. **Flexibility**: Environment-based configuration
6. **Security**: Automatic header redaction
