# Live Network Threat Telemetry API — MVP (Stage 4)

[![Docker CI](https://github.com/shervinhariri/telemetry-api/actions/workflows/docker.yml/badge.svg)](https://github.com/shervinhariri/telemetry-api/actions/workflows/docker.yml)

Production-ready telemetry API that ingests **Zeek `conn.log` JSON** and **network flows**, enriches with GeoIP/ASN + threat intelligence, and returns enriched JSON with risk scoring.

**Stage 4 Pro Dashboard**: Single-container deployment with modern web dashboard, real-time metrics visualization, and comprehensive API testing interface.

## 🎯 Stage Progression

- **Stage 1**: Basic API endpoints and data structures
- **Stage 2**: Contract alignment with all required endpoints
- **Stage 3**: Production deployment and testing framework
- **Stage 4**: **Pro Dashboard** - Single container with web UI

## 🚀 Quick Start

### Stage 4 Dashboard (Single Container)
```bash
cd ops/stage4
docker compose up -d
open http://localhost:8080  # Modern web dashboard
```

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

### Testing
```bash
./scripts/run_tests.sh  # Run all tests locally
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

## ✅ Stage 3 Contract Alignment

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
