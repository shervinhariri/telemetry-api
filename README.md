# Live Network Threat Telemetry API — MVP (Stage 3)

[![Docker CI](https://github.com/shervinhariri/telemetry-api/actions/workflows/docker.yml/badge.svg)](https://github.com/shervinhariri/telemetry-api/actions/workflows/docker.yml)

Production-ready telemetry API that ingests **Zeek `conn.log` JSON** and **network flows**, enriches with GeoIP/ASN + threat intelligence, and returns enriched JSON with risk scoring.

## 🚀 Quick Start

### Production Deployment (3 steps)
```bash
./scripts/bootstrap.sh
cp .env.example .env  # edit values
./scripts/deploy.sh
```

### Validation
```bash
./scripts/test_health.sh
./scripts/test_ingest.sh
```

### Outputs Configuration
```bash
./scripts/configure_splunk.sh
./scripts/configure_elastic.sh
```

## Quickstart (local)

1) Put MaxMind DBs + a sample threat CSV in `./data/`:
```
data/GeoLite2-City.mmdb
data/GeoLite2-ASN.mmdb
data/threats.csv
```

2) Build and run:
```bash
docker build -t telemetry-api:0.1.0 .
docker run -d -p 8080:8080 \
  -e API_KEY=TEST_KEY \
  -e GEOIP_DB_CITY=/data/GeoLite2-City.mmdb \
  -e GEOIP_DB_ASN=/data/GeoLite2-ASN.mmdb \
  -e THREATLIST_CSV=/data/threats.csv \
  -v $PWD/data:/data:ro \
  --name tel-api telemetry-api:0.1.0
```

3) Test:
```bash
curl -s http://localhost:8080/v1/health | jq .
curl -s -X POST http://localhost:8080/v1/ingest \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data @samples/zeek_conn.json | jq .
```

## 🔗 API Endpoints

- `GET /v1/health` - Health check
- `GET /v1/version` - API version info
- `GET /v1/schema` - Available schemas
- `POST /v1/ingest` - Ingest telemetry data (batch)
- `POST /v1/lookup` - Single IP enrichment
- `POST /v1/outputs/splunk` - Configure Splunk HEC
- `POST /v1/outputs/elastic` - Configure Elasticsearch
- `POST /v1/alerts/rules` - Configure alert rules
- `GET /v1/metrics` - Prometheus metrics (basic auth)

## 📊 Limits & Errors

- **Payload size**: 5MB maximum (gzipped)
- **Records per batch**: 10,000 maximum
- **Rate limiting**: 
  - Ingest: 120 req/min (configurable via `RATE_LIMIT_INGEST_RPM`)
  - Default: 600 req/min (configurable via `RATE_LIMIT_DEFAULT_RPM`)
- **Retention**: 7 days for deadletter queue
- **Error format**: JSON with `detail` field

## 🔧 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | Bearer token for authentication | `TEST_KEY` |
| `API_IMAGE` | Docker image name | `shvin/telemetry-api:latest` |
| `DOMAIN` | API domain | `api.yourdomain.com` |
| `GEOIP_DB_CITY` | MaxMind City database path | `/data/GeoLite2-City.mmdb` |
| `GEOIP_DB_ASN` | MaxMind ASN database path | `/data/GeoLite2-ASN.mmdb` |
| `THREATLIST_CSV` | Threat intelligence CSV | `/data/threats.csv` |
| `SPLUNK_HEC_URL` | Splunk HEC endpoint | - |
| `SPLUNK_HEC_TOKEN` | Splunk HEC token | - |
| `ELASTIC_URL` | Elasticsearch endpoint | - |
| `ELASTIC_USERNAME` | Elasticsearch username | - |
| `ELASTIC_PASSWORD` | Elasticsearch password | - |
| `BASIC_AUTH_USER` | Metrics endpoint username | `metrics` |
| `BASIC_AUTH_PASS` | Metrics endpoint password | `changeme` |
| `RATE_LIMIT_INGEST_RPM` | Ingest rate limit | `120` |
| `RATE_LIMIT_DEFAULT_RPM` | Default rate limit | `600` |

## Limits (from Step 2 – applied later)
- Format: `zeek.conn.v1` only in Stage 3
- Batch size/limits & rate limiting to be added in Stage 4
