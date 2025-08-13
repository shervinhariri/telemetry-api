# Live Network Threat Telemetry API

Local-first MVP to ingest NetFlow/IPFIX and Zeek JSON, enrich with GeoIP/ASN + threat intel, apply basic risk scoring, and ship SIEM-ready outputs.

![Build](https://github.com/shervinhariri/telemetry-api/actions/workflows/docker.yml/badge.svg)

## Project Stages & Status

- ✅ **Step 1: MVP Scope** — Inputs: NetFlow/IPFIX JSON (nfdump, pmacct, ntopng), Zeek JSON logs (conn.log, dns.log, ssl.log). Enrichments: GeoIP (MaxMind GeoLite2), ASN (Team Cymru), threat intel match, basic risk scoring (0–100). Outputs: Splunk HEC, Elastic bulk JSON, JSON download. Retention: 7 days. Exclusions: PCAP headers, TLS JA3, anomaly ML, QRadar, Datadog, Kafka.

- ✅ **Step 2: Data Models & API Contract** — Base URL: `/v1`, Bearer auth, endpoints: `/health`, `/ingest`, `/lookup`, `/outputs/splunk`, `/outputs/elastic`, `/alerts/rules`, `/metrics`. Input schemas: flows.v1 JSON, zeek.conn.v1, zeek.dns.v1. Output schema: enriched JSON with src/dst IP, ASN, GeoIP, threat matches, risk score, tags. Limits: max batch 5MB gzipped, 10k records, 600 req/min.

- ✅ **Step 3: Contract Alignment** — Containerized MVP build, verified API endpoints, schema validation, sample data ingestion working, CI pipeline added. Prepared for production deployment.

- ✅ **Step 4: Open-Source Launch** — Single container (API + Dashboard UI) with health, metrics, ingest, lookup, and output configuration in GUI. On-prem/cloud ready, Docker Hub publishing with `latest` and version tags. Focus on adoption via free open-source release.

- ✅ **Step 5: Production-Ready Ingest Pipeline** — Robust ingest endpoint with queue-based processing, gzip support, proper error handling (4xx/5xx), and background worker pipeline. Accepts raw JSON arrays and wrapped `{"records": [...]}` format. Backpressure handling with 429 responses.

- 🟣 **Step 5.1: Version Management & Output Connectors (current)** — Version badge with update notifications, Docker Hub integration, Stage 5.1 output connector configuration endpoints (Splunk HEC, Elastic bulk), and dev-safe update mechanism. Foundation for Stage 5.2 dispatcher wiring.

> Current version: **v0.5.1** (Patch 5.1 - version management + output connectors).  
> Docs for Steps 1–2 are in `/docs/` and PDFs.

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
Docker Hub: shvin/telemetry-api:latest, shvin/telemetry-api:v0.5.1

GitHub Tags: v0.5.1 (Patch 5.1)

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

## 🚀 Stage 5 Features

### Robust Ingest Pipeline
- **Dual Format Support**: Accepts both raw JSON arrays `[...]` and wrapped `{"records": [...]}`
- **Gzip Compression**: Auto-detects gzip via header or magic number (`1F 8B`)
- **Queue-Based Processing**: Records processed asynchronously via background worker
- **Backpressure Handling**: Returns 429 when queue is full (10k limit)
- **Proper Error Handling**: 4xx for client errors, 5xx only for server faults

### Input Validation
- **Timestamp Required**: Records must have `ts`, `time`, or `@timestamp` field
- **Size Limits**: 5MB gzipped, 10k records per batch
- **JSON Validation**: Proper UTF-8 encoding and valid JSON structure
- **Graceful Degradation**: Queue full → 429 with retry guidance

### Background Processing
- **Async Worker Loop**: Processes records from queue in background
- **Error Isolation**: Worker failures don't affect ingest endpoint
- **Dead Letter Queue**: Failed records written to files for analysis
- **Queue Metrics**: Real-time queue depth and processing status

### API Endpoints
- **`/v1/health`**: Public health check (no auth required)
- **`/v1/version`**: Version information and metadata
- **`/v1/updates/check`**: Docker Hub update availability check
- **`/v1/ingest`**: Robust ingest with queue processing
- **`/v1/metrics`**: Queue depth and processing metrics
- **`/v1/lookup`**: IP/domain enrichment (requires auth)
- **`/v1/outputs/splunk`**: Splunk HEC configuration (requires auth)
- **`/v1/outputs/elastic`**: Elasticsearch configuration (requires auth)
- **`/v1/admin/update`**: Dev-only image update (requires admin token)

## 🚀 Patch 5.1 Features

### Version Management & Update Notifications
- **Version Badge**: Real-time version display in GUI with update notifications
- **Docker Hub Integration**: Automatic checking for newer images every 60 seconds
- **Update Notifications**: Green badge = up-to-date, Amber badge = update available
- **Dev-Safe Updates**: One-click image pulling with admin token (development only)
- **Production Updates**: Watchtower integration for automatic container updates

### Stage 5.1 Output Connectors
- **Splunk HEC Configuration**: Full HEC endpoint configuration with batching and retry settings
- **Elasticsearch Configuration**: Multi-node Elasticsearch setup with bulk indexing
- **Configuration Persistence**: In-memory storage of connector settings
- **Validation**: Pydantic models ensure proper configuration format
- **API Contract Compliance**: Implements Step-2 contract endpoints exactly

### Update Mechanisms
```bash
# Check version
curl -s http://localhost:8080/v1/version

# Check for updates
curl -s http://localhost:8080/v1/updates/check

# Dev-only: pull latest image
curl -s -X POST http://localhost:8080/v1/admin/update -H "X-Admin-Token: $ADMIN_TOKEN"

# Configure Splunk HEC
curl -s -X POST http://localhost:8080/v1/outputs/splunk \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data '{"hec_url":"https://splunk.example:8088/services/collector","token":"***","index":"telemetry"}'

# Configure Elasticsearch
curl -s -X POST http://localhost:8080/v1/outputs/elastic \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data '{"urls":["https://es1:9200"],"index_prefix":"telemetry-","bulk_size":1000}'
```

### Production Deployment
For production environments, use Watchtower for automatic updates:
```yaml
# docker-compose.yml
services:
  watchtower:
    image: containrrr/watchtower
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --cleanup --interval 60 telemetry-api
```

## 🧪 Development & Testing

### Local Development
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

### Running Tests
```bash
# Run all tests (unit, integration, schema validation)
./scripts/run_tests.sh

# Run specific test categories
python -m pytest tests/test_api.py -v
python tests/validate_schemas.py
```

## 🎨 Stage 4 Dashboard Features

- **Modern Dark Theme** with responsive design
- **Real-time KPI Cards** with sparklines (Events, Sources, Batches, Threats, Risk, Lag)
- **Interactive Charts** using Chart.js (Events per minute)
- **API Testing Interface** with tabs for:
  - Ingest Test (JSON batch testing)
  - Outputs (Splunk/Elastic configuration)
  - Lookup (IP/domain enrichment)
  - System (Health and metrics)
- **Auto-refresh** every 5 seconds
- **Bearer Authentication** support

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

## ✅ Stage 4 Pro Dashboard

This version is fully aligned with Step 1-2 specifications:

### ✅ **Endpoint Parity**
- All required endpoints implemented with proper authentication
- X-API-Version header middleware for versioning
- Proper error handling with JSON responses
- Health checks and metrics endpoints

### ✅ **Rate Limiting**
- Environment-driven configuration
- Contract-compliant defaults (120/600 req/min)
- Configurable for trusted environments
- Caddy-based implementation with burst handling

### ✅ **Data Validation**
- JSON schemas for all data formats
- Schema validation in CI pipeline
- Sample data with proper validation
- Input/output format compliance

### ✅ **Testing & Quality**
- Comprehensive unit and integration tests
- Schema validation for sample data
- CI integration with GitHub Actions
- Local test runner for development

### ✅ **Production Readiness**
- Complete deployment automation
- Security configurations (UFW, fail2ban)
- Monitoring and logging setup
- Deadletter handling for reliability

## 📚 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide
- **[STAGE3_CHECKLIST.md](STAGE3_CHECKLIST.md)** - Complete deliverables checklist
- **[schemas/](schemas/)** - JSON schema definitions
- **[tests/](tests/)** - Test suite and validation scripts


