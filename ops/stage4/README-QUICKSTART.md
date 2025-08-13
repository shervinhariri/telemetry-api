# Stage 4 — Pro Dashboard (Single Container)

This stage ships:
- `telemetry-api` (port 8080) - serves both API and dashboard UI
- Attractive dashboard with KPI cards, sparklines, and an Events/min chart
- Tabs for Ingest Test, Outputs (Splunk/Elastic), Lookup, and System

## Run
```bash
cd ops/stage4
docker compose up -d
# Dashboard
open http://localhost:8080
# API health
curl -s http://localhost:8080/v1/health -H "Authorization: Bearer TEST_KEY"
```

## Smoke Tests

### Health
```bash
curl -i http://localhost:8080/v1/health -H "Authorization: Bearer TEST_KEY"
```

### Ingest (sample)
```bash
curl -s -X POST http://localhost:8080/v1/ingest \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data '{"format": "flows.v1", "records": [{"ts": 1723290000, "src_ip":"10.0.0.10", "dst_ip":"1.1.1.1", "src_port":12345, "dst_port":53, "proto":"udp", "bytes":84, "packets":1, "app":"dns"}]}' | jq .
```

### Configure Splunk
```bash
curl -s -X POST http://localhost:8080/v1/outputs/splunk \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data '{"url":"https://splunk.example.com:8088/services/collector","token":"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"}' | jq .
```

### Configure Elastic
```bash
curl -s -X POST http://localhost:8080/v1/outputs/elastic \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data '{"url":"https://es.example.com:9200","index":"telemetry-events","username":"elastic","password":"changeme"}' | jq .
```

## What to expect

Dashboard shows "—" until /metrics exposes counters/gauges.

Events/min chart starts updating every 5s; send an ingest to see the curve rise.

KPI fields read from Prometheus:
- `telemetry_ingest_total`
- `telemetry_threat_matches_total`
- `telemetry_risk_score_sum` / `telemetry_risk_score_count`
- `telemetry_queue_lag_gauge`
- `telemetry_sources_active`
- `telemetry_batches_total`

## Troubleshooting

- **UI blank?** Ensure container is up: `docker ps`
- **No metrics?** Hit `/v1/metrics` directly and verify names
- **UI served from** `/` and also available under `/ui` path
