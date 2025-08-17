# Telemetry API — v0.8.0

Fast, local network telemetry enrichment with GeoIP, ASN, threat intelligence, and risk scoring. Ship to Splunk/Elastic with request-level observability.

![Build](https://github.com/shervinhariri/telemetry-api/actions/workflows/docker.yml/badge.svg)

## TL;DR

Ingest NetFlow/IPFIX and Zeek JSON → enrich with GeoIP/ASN/threat intel → apply risk scoring → export to Splunk/Elastic. All with request-level audit and performance dashboards.

## 🚀 Validate in 60 seconds

```bash
# 1) Run container
docker run -d -p 8080:8080 \
  -e API_KEY=TEST_KEY \
  -e REDACT_HEADERS=authorization \
  --name telapi shvin/telemetry-api:0.8.0

# 2) Ingest sample Zeek
curl -s -X POST http://localhost:8080/v1/ingest/zeek \
  -H "Authorization: Bearer TEST_KEY" -H "Content-Type: application/json" \
  --data @samples/zeek_conn_small.json | jq

# 3) See it live
open http://localhost:8080/docs  # API documentation
open http://localhost:8080       # Dashboard

# 4) Download enriched output
curl -s "http://localhost:8080/v1/download/json?limit=50" \
  -H "Authorization: Bearer TEST_KEY" | head -n 5
```

## Quick Start

```bash
# Single container with MaxMind/TI data
docker run -d -p 8080:8080 \
  -e API_KEY=TEST_KEY \
  -e GEOIP_DB_CITY=/data/GeoLite2-City.mmdb \
  -e GEOIP_DB_ASN=/data/GeoLite2-ASN.mmdb \
  -e THREATLIST_CSV=/data/threats.csv \
  -v $PWD/data:/data:ro \
  --name telemetry-api shvin/telemetry-api:0.8.0

# Open dashboard
open http://localhost:8080

# Test ingest
curl -s -X POST http://localhost:8080/v1/ingest/zeek \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data @samples/zeek_conn_small.json | jq
```

## 🎯 Quickstart (Demo Mode + Prometheus)

Get up and running with demo data and monitoring in 5 minutes:

```bash
# 1) Run with demo mode enabled
docker run -d -p 8080:8080 \
  -e API_KEY=TEST_KEY \
  -e DEMO_MODE=true \
  -e DEMO_EPS=50 \
  -e DEMO_DURATION_SEC=120 \
  --name telemetry-api-demo shvin/telemetry-api:latest

# 2) Start demo generator
curl -s -X POST http://localhost:8080/v1/demo/start \
  -H "Authorization: Bearer TEST_KEY" | jq

# 3) Check Prometheus metrics
curl -s http://localhost:8080/v1/metrics/prometheus | head -20

# 4) View dashboard
open http://localhost:8080

# 5) Stop demo when done
curl -s -X POST http://localhost:8080/v1/demo/stop \
  -H "Authorization: Bearer TEST_KEY" | jq
```

### Grafana Dashboard

1. **Import Dashboard**: Use `dashboards/grafana/telemetry-api.json`
2. **Configure Prometheus**: Add Prometheus data source pointing to `http://localhost:8080/v1/metrics/prometheus`
3. **View Metrics**: Dashboard shows EPS, latency, threat matches, and more

### Demo Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DEMO_MODE` | `false` | Enable demo mode |
| `DEMO_EPS` | `50` | Events per second |
| `DEMO_DURATION_SEC` | `120` | Demo duration in seconds |
| `DEMO_VARIANTS` | `netflow,zeek` | Event types to generate |

### Troubleshooting

- **Demo not starting**: Check `DEMO_MODE=true` and API key has admin scope
- **No metrics**: Verify `/v1/metrics/prometheus` endpoint is accessible
- **Grafana import fails**: Ensure Prometheus data source is configured correctly
```

## 📊 Features

### Supported Inputs

#### Zeek conn.log JSON
```json
{
  "ts": 1642176000.0,
  "uid": "C1234567890abcdef",
  "id.orig_h": "192.168.1.100",
  "id.orig_p": 54321,
  "id.resp_h": "8.8.8.8",
  "id.resp_p": 53,
  "proto": "udp",
  "service": "dns"
}
```

#### NetFlow/IPFIX JSON
```json
{
  "timestamp": 1642176000,
  "src_ip": "192.168.1.100",
  "dst_ip": "8.8.8.8",
  "src_port": 54321,
  "dst_port": 53,
  "protocol": 17,
  "bytes": 192,
  "packets": 2
}
```

**Endpoints**: `POST /v1/ingest/zeek`, `POST /v1/ingest/netflow`, `POST /v1/ingest/bulk`

### Enrichment Pipeline

- **GeoIP**: Country, city, location (MaxMind GeoLite2)
- **ASN**: Autonomous system number and organization
- **Threat Intelligence**: IP/CIDR matching with confidence scoring
- **Risk Scoring**: 0-10 scale based on threat matches and context

### Outputs

- **Splunk HEC**: `POST /v1/export/splunk-hec` (buffered bulk)
- **Elasticsearch**: `POST /v1/export/elastic` (bulk JSON)
- **JSON Download**: `GET /v1/download/json?limit=10000`

### Observability Dashboard

- **Real-time Metrics**: Throughput chart + stat cards (Queue Lag, Avg Risk, Threat Matches, Error Rate)
- **Request Audit**: Live tail with Server-Sent Events + detailed request inspection
- **System Monitoring**: `GET /v1/system` with backpressure signals and DLQ status
- **API Documentation**: Interactive Swagger UI at `/docs`

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | `TEST_KEY` | Bearer token for authentication |
| `GEOIP_DB_CITY` | `/data/GeoLite2-City.mmdb` | MaxMind City database path |
| `GEOIP_DB_ASN` | `/data/GeoLite2-ASN.mmdb` | MaxMind ASN database path |
| `THREATLIST_CSV` | `/data/threats.csv` | Threat intelligence CSV file |
| `SPLUNK_HEC_URL` | - | Splunk HEC endpoint URL |
| `SPLUNK_HEC_TOKEN` | - | Splunk HEC token |
| `ELASTIC_URL` | - | Elasticsearch URL |
| `ELASTIC_USERNAME` | - | Elasticsearch username |
| `ELASTIC_PASSWORD` | - | Elasticsearch password |
| `REDACT_HEADERS` | - | Comma-separated headers to redact in logs |

## 📈 Limits & Performance

- **Batch Size**: 10,000 records max
- **Payload Size**: 5MB max (gzip supported)
- **Rate Limit**: 600 requests/minute
- **Retention**: 7 days (rolling files)
- **Queue Depth**: 10,000 records
- **Dead Letter Queue**: Failed exports with retry logic

## 🔧 Development

### Local Development
```bash
# Clone and setup
git clone https://github.com/shervinhariri/telemetry-api.git
cd telemetry-api

# Build and run
docker build -t telemetry-api:local .
docker run -d -p 8080:8080 -e API_KEY=TEST_KEY --name telemetry-api telemetry-api:local

# Test
curl -s http://localhost:8080/v1/health | jq
```

### Testing
```bash
# Health check
./scripts/test_health.sh

# Ingest test
./scripts/test_ingest.sh

# Full test suite
./scripts/run_tests.sh
```

### Output Configuration
```bash
# Splunk HEC setup
./scripts/configure_splunk.sh

# Elasticsearch setup
./scripts/configure_elastic.sh
```

## 📚 API Documentation

- **Interactive Docs**: `http://localhost:8080/docs` (Swagger UI)
- **OpenAPI Spec**: `http://localhost:8080/openapi.yaml`
- **Health Check**: `GET /v1/health`
- **System Info**: `GET /v1/system`
- **Metrics**: `GET /v1/metrics`

## 🚀 Production Deployment

### Docker Compose
```yaml
version: '3.8'
services:
  telemetry-api:
    image: shvin/telemetry-api:0.8.0
    ports:
      - "8080:8080"
    environment:
      - API_KEY=your-secure-key
      - SPLUNK_HEC_URL=https://your-splunk:8088
      - SPLUNK_HEC_TOKEN=your-hec-token
    volumes:
      - ./data:/data:ro
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: telemetry-api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: telemetry-api
  template:
    metadata:
      labels:
        app: telemetry-api
    spec:
      containers:
      - name: telemetry-api
        image: shvin/telemetry-api:0.8.0
        ports:
        - containerPort: 8080
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: telemetry-secrets
              key: api-key
```

## 📋 Changelog

### v0.8.0 (Current)
- ✅ OpenAPI 3.1 specification with Swagger UI
- ✅ Scoped API keys with RBAC (ingest, manage_indicators, export, read_requests, read_metrics)
- ✅ Security headers and configurable field redaction
- ✅ Dead Letter Queue (DLQ) for export failures with exponential backoff
- ✅ Idempotency support for ingest operations
- ✅ Enhanced observability with detailed metrics and system monitoring
- ✅ Real-time dashboard with Server-Sent Events for live tailing
- ✅ Comprehensive request audit logging

### v0.7.8
- Enhanced UI with real-time metrics
- Improved error handling and logging
- Better data transformation and normalization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🔗 Links

- **Docker Hub**: [shvin/telemetry-api](https://hub.docker.com/r/shvin/telemetry-api)
- **GitHub**: [shervinhariri/telemetry-api](https://github.com/shervinhariri/telemetry-api)
- **Issues**: [GitHub Issues](https://github.com/shervinhariri/telemetry-api/issues)


