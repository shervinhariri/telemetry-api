# Live Network Threat Telemetry API

Local-first MVP to ingest NetFlow/IPFIX and Zeek JSON, enrich with GeoIP/ASN + threat intel, apply basic risk scoring, and ship SIEM-ready outputs.

![Build](https://github.com/shervinhariri/telemetry-api/actions/workflows/docker.yml/badge.svg)

## Project Stages & Status

- ✅ **Step 1: MVP Scope** — Inputs: NetFlow/IPFIX JSON (nfdump, pmacct, ntopng), Zeek JSON logs (conn.log, dns.log, ssl.log). Enrichments: GeoIP (MaxMind GeoLite2), ASN (Team Cymru), threat intel match, basic risk scoring (0–100). Outputs: Splunk HEC, Elastic bulk JSON, JSON download. Retention: 7 days. Exclusions: PCAP headers, TLS JA3, anomaly ML, QRadar, Datadog, Kafka.

- ✅ **Step 2: Data Models & API Contract** — Base URL: `/v1`, Bearer auth, endpoints: `/health`, `/ingest`, `/lookup`, `/outputs/splunk`, `/outputs/elastic`, `/alerts/rules`, `/metrics`. Input schemas: flows.v1 JSON, zeek.conn.v1, zeek.dns.v1. Output schema: enriched JSON with src/dst IP, ASN, GeoIP, threat matches, risk score, tags. Limits: max batch 5MB gzipped, 10k records, 600 req/min.

- ✅ **Step 3: Contract Alignment** — Containerized MVP build, verified API endpoints, schema validation, sample data ingestion working, CI pipeline added. Prepared for production deployment.

- ✅ **Step 4: Open-Source Launch** — Single container (API + Dashboard UI) with health, metrics, ingest, lookup, and output configuration in GUI. On-prem/cloud ready, Docker Hub publishing with `latest` and version tags. Focus on adoption via free open-source release.

- ✅ **Step 5: Production-Ready Ingest Pipeline** — Robust ingest endpoint with queue-based processing, gzip support, proper error handling (4xx/5xx), and background worker pipeline. Accepts raw JSON arrays and wrapped `{"records": [...]}` format. Backpressure handling with 429 responses.

- ✅ **Step 5.1: Version Management & Output Connectors** — Version badge with update notifications, Docker Hub integration, Stage 5.1 output connector configuration endpoints (Splunk HEC, Elastic bulk), and dev-safe update mechanism. Foundation for Stage 5.2 dispatcher wiring.

- ✅ **Step 6: Deploy & Host MVP** — Activated processing pipeline workers, file sink for daily NDJSON, stats/events/download endpoints, Logs tab with live tail and file upload, minimal version indicator, and clean header design.

- 🟣 **Step 7: Request Observability (v0.7.5) - CURRENT** — Professional minimal dashboard (6 cards), request audit system with operations tracking, system info endpoint, enhanced UI with status codes and sparklines, performance optimizations.

> Current version: **v0.7.5** (Professional Dashboard & Request Observability).  
> Docs for Steps 1–7 are in `/docs/` and PDFs.

## Quickstart
```bash
# run single container (API + UI)
docker run -d -p 8080:8080 \
  -e API_KEYS=TEST_KEY \
  --name telemetry-api shvin/telemetry-api:latest

# open UI
open http://localhost:8080

# health (no auth required)
curl -s http://localhost:8080/v1/health | jq .

# ingest - raw array format
curl -s -X POST http://localhost:8080/v1/ingest \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data '[{"ts": 1723290000, "src_ip":"10.0.0.10", "dst_ip":"1.1.1.1", "src_port":12345, "dst_port":53, "proto":"udp", "bytes":84, "packets":1, "app":"dns"}]' | jq .

# ingest - wrapped format (also supported)
curl -s -X POST http://localhost:8080/v1/ingest \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data '{"records": [{"ts": 1723290000, "src_ip":"10.0.0.10", "dst_ip":"1.1.1.1", "src_port":12345, "dst_port":53, "proto":"udp", "bytes":84, "packets":1, "app":"dns"}]}' | jq .

# ingest with gzip compression
echo '[{"ts": 1723290000, "src_ip":"10.0.0.10", "dst_ip":"1.1.1.1"}]' | gzip | curl -s -X POST http://localhost:8080/v1/ingest \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  -H "Content-Encoding: gzip" \
  --data-binary @- | jq .
```

## Release & Images
Docker Hub: shvin/telemetry-api:latest, shvin/telemetry-api:v0.7.5

GitHub Tags: v0.7.5 (Step 7 - Request Observability)

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

### Testing
```bash
./scripts/run_tests.sh  # Run all tests locally
```

## 🚀 Core Features

### Robust Ingest Pipeline
- **Dual Format Support**: Accepts both raw JSON arrays `[...]` and wrapped `{"records": [...]}`
- **Gzip Compression**: Auto-detects gzip via header or magic number (`1F 8B`)
- **Queue-Based Processing**: Records processed asynchronously via background worker
- **Backpressure Handling**: Returns 429 when queue is full (10k limit)
- **Proper Error Handling**: 4xx for client errors, 5xx only for server faults

### Request Observability (v0.7.5)
- **Professional Dashboard**: 6 KPI cards with live sparklines and status indicators
- **Request Audit Trail**: Complete request logging with operations tracking
- **System Monitoring**: Structured system information and metrics
- **Live Tail**: Real-time request monitoring with filters and export



## 🚀 Step 7 Features (v0.7.5)

### Professional Minimal Dashboard
- **6 KPI Cards**: Events, Threats, Risk, Requests (15m), Status Codes, P95 Latency
- **Live Sparklines**: Real-time trend visualization for each metric
- **Status Code Pills**: 2xx/4xx/5xx breakdown with color coding
- **Clean Design**: Removed clutter, focused on essential metrics
- **Auto-refresh**: Updates every 5 seconds with smooth animations

### Request Observability System
- **Audit Trail**: Complete request logging with operations data
- **Operations Tracking**: Detailed breakdown of what happened per request
- **System Info**: Structured `/v1/system` endpoint with bounded JSON
- **Request Details**: Individual request inspection with full context
- **Live Tail**: Real-time request monitoring with filters

### Enhanced API Endpoints
- **`/v1/system`**: Structured system information (version, uptime, workers, metrics)
- **`/v1/admin/requests`**: Paginated request audit log
- **`/v1/admin/requests/summary`**: Request summary metrics (15m window)
- **`/v1/admin/requests/{id}`**: Detailed request information with operations

### Performance Optimizations
- **Lightweight Dependencies**: Removed unnecessary packages (pytest, jsonschema, reportlab)
- **Faster Startup**: Optimized container build and initialization
- **Memory Efficient**: In-memory audit with 7-day retention
- **Async Processing**: Non-blocking request handling

### Professional UI Enhancements
- **System Tab Fix**: No more overflow, bounded JSON display
- **Copy Functionality**: One-click copying of system information
- **Status Indicators**: Color-coded status badges and result indicators
- **Responsive Design**: Maintains professional appearance on all devices

### Quick Test Steps for v0.7.3
```bash
# 1. Check system information
curl -s http://localhost:8080/v1/system | jq

# 2. View request summary
curl -s http://localhost:8080/v1/admin/requests/summary | jq

# 3. Check request audit log
curl -s http://localhost:8080/v1/admin/requests | jq '.items | length'

# 4. Send test requests
curl -X POST http://localhost:8080/v1/lookup \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  -d '{"ip":"8.8.8.8"}'

# 5. View updated dashboard metrics
curl -s http://localhost:8080/v1/metrics | jq '.totals'
```



## 🧪 Development & Testing

### Local Development
```bash
# Build and run
docker build -t telemetry-api:latest .
docker run -d -p 8080:8080 -e APP_VERSION=0.7.2 telemetry-api:latest

# Test endpoints
curl http://localhost:8080/v1/health
curl http://localhost:8080/v1/system
curl http://localhost:8080/v1/admin/requests/summary
```



## 🔗 API Endpoints

### Core Endpoints
- `GET /v1/health` - Health check
- `GET /v1/version` - API version info
- `GET /v1/schema` - Available schemas
- `POST /v1/ingest` - Ingest telemetry data (batch)
- `POST /v1/lookup` - Single IP enrichment
- `POST /v1/outputs/splunk` - Configure Splunk HEC
- `POST /v1/outputs/elastic` - Configure Elasticsearch
- `POST /v1/alerts/rules` - Configure alert rules
- `GET /v1/metrics` - Prometheus metrics (basic auth)

### Observability Endpoints (v0.7.5)
- `GET /v1/system` - Structured system information
- `GET /v1/admin/requests` - Request audit log (paginated)
- `GET /v1/admin/requests/summary` - Request summary metrics
- `GET /v1/admin/requests/{id}` - Detailed request information

## 📊 Limits & Errors

- **Payload size**: 5MB maximum (gzipped)
- **Records per batch**: 10,000 maximum
- **Rate limiting**: 
  - Ingest: 120 req/min (configurable via `RATE_LIMIT_INGEST_RPM`)
  - Default: 600 req/min (configurable via `RATE_LIMIT_DEFAULT_RPM`)
- **Retention**: 7 days for deadletter queue
- **Error format**: JSON with `detail` field
- **Authentication**: Bearer token required for all endpoints except `/v1/health`
- **Versioning**: All responses include `X-API-Version` header

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
| `TZ` | Timezone | `UTC` |

## 📋 Data Formats

### Supported Input Formats
- **`zeek.conn.v1`** - Zeek connection logs
- **`flows.v1`** - Network flow data

### Enriched Output
All records include:
- **GeoIP data** (country, city, coordinates)
- **ASN information** (ASN number, organization)
- **Threat intelligence** (matches, categories, confidence)
- **Risk scoring** (0-100 scale with reasons)
- **Tags** for categorization

## 🔒 Security Features

- **HTTPS/TLS** with automatic Let's Encrypt certificates
- **Rate limiting** to prevent abuse
- **Basic authentication** for metrics endpoint
- **CORS headers** for cross-origin requests
- **Security headers** (X-Content-Type-Options, X-Frame-Options, etc.)
- **UFW firewall** configuration
- **Fail2ban** for brute force protection

## 📈 Monitoring & Operations

- **Health checks** with automatic restart
- **Prometheus metrics** endpoint
- **Structured logging** in JSON format
- **Log rotation** for Caddy access/error logs
- **Deadletter queue** for failed output processing
- **Comprehensive test suite** with CI integration

## 🚀 CI/CD Pipeline

- **Automated testing** on pull requests
- **Schema validation** in CI pipeline
- **Docker image builds** on version tags
- **Security scanning** and dependency updates
- **Deployment automation** scripts

## 📚 Documentation

- **[docs/](docs/)** - Project documentation and PDFs
- **[schemas/](schemas/)** - JSON schema definitions


