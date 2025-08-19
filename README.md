# Telemetry API — v0.8.2

Fast, local network telemetry enrichment with GeoIP, ASN, threat intelligence, and risk scoring. Ship to Splunk/Elastic with request-level observability and multi-tenant authentication.

![Build](https://github.com/shervinhariri/telemetry-api/actions/workflows/docker.yml/badge.svg)

## TL;DR

Ingest NetFlow/IPFIX and Zeek JSON → enrich with GeoIP/ASN/threat intel → apply risk scoring → export to Splunk/Elastic. All with request-level audit and performance dashboards.

## 🚀 Validate in 60 seconds

```bash
# 1) Run container
docker run -d -p 80:80 \
  -e API_KEY=TEST_KEY \
  -e REDACT_HEADERS=authorization \
  --name telapi shvin/telemetry-api:0.8.2

# 2) Ingest sample Zeek
curl -s -X POST http://localhost/v1/ingest/zeek \
  -H "Authorization: Bearer TEST_KEY" -H "Content-Type: application/json" \
  --data @samples/zeek_conn_small.json | jq

# 3) See it live
open http://localhost/docs  # API documentation
open http://localhost       # Dashboard

# 4) Download enriched output
curl -s "http://localhost/v1/download/json?limit=50" \
  -H "Authorization: Bearer TEST_KEY" | head -n 5
```

## Quick Start

```bash
# Single container with MaxMind/TI data
docker run -d -p 80:80 \
  -e API_KEY=TEST_KEY \
  -e GEOIP_DB_CITY=/data/GeoLite2-City.mmdb \
  -e GEOIP_DB_ASN=/data/GeoLite2-ASN.mmdb \
  -e THREATLIST_CSV=/data/threats.csv \
  -v $PWD/data:/data:ro \
  --name telemetry-api shvin/telemetry-api:0.8.2

# Open dashboard
open http://localhost

# Test ingest
curl -s -X POST http://localhost/v1/ingest/zeek \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data @samples/zeek_conn_small.json | jq
```

## 📊 Structured Logging

The API now includes production-ready structured logging with:

- **JSON logs** for production environments
- **Queue-based async logging** to prevent blocking
- **Intelligent sampling** (1% of successful requests by default)
- **Trace ID correlation** across request → pipeline → output
- **Environment-based configuration** for dev vs production

### Development Mode
```bash
# Human-readable logs with emojis
export ENVIRONMENT=development
export LOG_FORMAT=text
export HTTP_LOG_SAMPLE_RATE=1.0  # Log all requests
```

## Golden Release and Rollback

This repository maintains a golden tag for the stable build of 0.8.2:

- Git tag: `v0.8.2-golden`
- Docker image: `shvin/telemetry-api:0.8.2-golden`

Rollback instructions:

```bash
git fetch --tags
git checkout v0.8.2-golden

docker pull shvin/telemetry-api:0.8.2-golden
docker rm -f telemetry-api || true
docker run -d -p 80:80 \
  -v $PWD/telemetry.db:/app/telemetry.db \
  --name telemetry-api \
  shvin/telemetry-api:0.8.2-golden
```

### Production Mode
```bash
# JSON logs with sampling
export ENVIRONMENT=production
export LOG_FORMAT=json
export HTTP_LOG_SAMPLE_RATE=0.01  # Sample 1% of successful requests
export HTTP_LOG_EXCLUDE_PATHS=/health,/metrics,/system
```

See [docs/LOGGING.md](docs/LOGGING.md) for complete configuration options.

## 🎯 Quickstart (Demo Mode + Prometheus)

Get up and running with demo data and monitoring in 5 minutes:

```bash
# 1) Run with demo mode enabled
docker run -d -p 80:80 \
  -e API_KEY=TEST_KEY \
  -e DEMO_MODE=true \
  -e DEMO_EPS=50 \
  -e DEMO_DURATION_SEC=120 \
  --name telemetry-api-demo shvin/telemetry-api:0.8.2

# 2) Start demo generator
curl -s -X POST http://localhost/v1/demo/start \
  -H "Authorization: Bearer TEST_KEY" | jq

# 3) Check Prometheus metrics
curl -s http://localhost/v1/metrics/prometheus | head -20

# 4) View dashboard
open http://localhost

# 5) Stop demo when done
curl -s -X POST http://localhost/v1/demo/stop \
  -H "Authorization: Bearer TEST_KEY" | jq
```

### Grafana Dashboard

1. **Import Dashboard**: Use `dashboards/grafana/telemetry-api.json`
2. **Configure Prometheus**: Add Prometheus data source pointing to `http://localhost/v1/metrics/prometheus`
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

## 🏢 Multi-Tenancy (v0.8.2)

The API now supports multi-tenant deployments with complete data isolation:

### Tenant Features
- **Database-backed tenants**: SQLite/PostgreSQL with proper foreign keys
- **Per-tenant API keys**: Scoped authentication with admin override
- **Data isolation**: All events, DLQ, and logs separated by tenant
- **Configurable retention**: Per-tenant retention policies (default: 7 days)
- **Admin override**: `X-Tenant-ID` header for cross-tenant operations

### Quick Multi-Tenant Setup

```bash
# 1) Run with database persistence
docker run -d -p 80:80 \
  -v $PWD/telemetry.db:/app/telemetry.db \
  --name telemetry-api shvin/telemetry-api:0.8.2

# 2) Database will auto-initialize with default tenant
# 3) Get admin API key from logs or use seed script
docker logs telemetry-api | grep "API Key:"

# 4) Use admin key for cross-tenant operations
curl -H "Authorization: Bearer ADMIN_KEY" \
     -H "X-Tenant-ID: tenant1" \
     http://localhost/v1/metrics
```

### Authentication & Authorization

- **API Keys**: Database-backed with SHA256 hashing
- **Scopes**: `admin`, `read_metrics`, `read_requests`, `export`
- **Admin Privileges**: Super-user access across all tenants
- **Public Endpoints**: `/v1/health`, `/v1/version`, `/docs`, `/ui/`

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./telemetry.db` | Database connection |
| `PUBLIC_PROMETHEUS` | `true` | Make metrics endpoint public |
| `DEV_BYPASS_SCOPES` | `false` | Development scope bypass |
```

## 🏢 Multi-Tenancy (v0.8.2)

The API now supports multi-tenant deployments with complete data isolation:

### Tenant Features
- **Database-backed tenants**: SQLite/PostgreSQL with proper foreign keys
- **Per-tenant API keys**: Scoped authentication with admin override
- **Data isolation**: All events, DLQ, and logs separated by tenant
- **Configurable retention**: Per-tenant retention policies (default: 7 days)
- **Admin override**: `X-Tenant-ID` header for cross-tenant operations

### Quick Multi-Tenant Setup

```bash
# 1) Run with database persistence
docker run -d -p 80:80 \
  -e DATABASE_URL=sqlite:///./telemetry.db \
  -e ADMIN_API_KEY=YOUR_ADMIN_KEY \
  -v $PWD/data:/data \
  --name telemetry-api shvin/telemetry-api:0.8.2

# 2) Create default tenant and admin key
docker exec telemetry-api python3 scripts/seed_default_tenant.py

# 3) Test tenant isolation
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" http://localhost/v1/health
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" -H "X-Tenant-ID: default" http://localhost/v1/health
```

### Tenant Management

```bash
# Create new tenant (admin only)
curl -X POST http://localhost/v1/admin/tenants \
  -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "acme-prod", "name": "ACME Production", "retention_days": 30}'

# Create tenant API key
curl -X POST http://localhost/v1/admin/keys \
  -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "acme-prod", "scopes": ["ingest", "read_metrics"]}'
```

### Backward Compatibility

- **Zero breaking changes**: All existing `/v1/*` endpoints work unchanged
- **Legacy API keys**: Continue to work with full admin access
- **Same retention**: Default 7-day retention maintained
- **Same Bearer auth**: No changes to authentication model

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
docker run -d -p 80:80 -e API_KEY=TEST_KEY --name telemetry-api telemetry-api:local

# Test
curl -s http://localhost/v1/health | jq
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

- **Interactive Docs**: `http://localhost/docs` (Swagger UI)
- **OpenAPI Spec**: `http://localhost/openapi.yaml`
- **Health Check**: `GET /v1/health`
- **System Info**: `GET /v1/system`
- **Metrics**: `GET /v1/metrics`

## 🚀 Production Deployment

### Docker Compose
```yaml
version: '3.8'
services:
  telemetry-api:
    image: shvin/telemetry-api:0.8.2
    ports:
      - "80:80"
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
        image: shvin/telemetry-api:0.8.2
        ports:
        - containerPort: 80
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: telemetry-secrets
              key: api-key
```

## 📋 Changelog

### v0.8.2 (Current)
- ✅ **Multi-Tenancy Support**: Complete tenant isolation with database-backed tenants
- ✅ **Database Models**: SQLAlchemy models for Tenant, ApiKey, OutputConfig, and Job
- ✅ **Tenant-Scoped Authentication**: Per-tenant API keys with scope validation
- ✅ **Admin Override**: X-Tenant-ID header for cross-tenant operations
- ✅ **Data Isolation**: All events, DLQ, and logs separated by tenant
- ✅ **Configurable Retention**: Per-tenant retention policies (default: 7 days)
- ✅ **Alembic Migrations**: Database schema management with proper foreign keys
- ✅ **Backward Compatibility**: All existing endpoints work unchanged
- ✅ **OpenAPI 3.1 specification** with Swagger UI
- ✅ **Scoped API keys** with RBAC (ingest, manage_indicators, export, read_requests, read_metrics)
- ✅ **Security headers** and configurable field redaction
- ✅ **Dead Letter Queue (DLQ)** for export failures with exponential backoff
- ✅ **Idempotency support** for ingest operations
- ✅ **Enhanced observability** with detailed metrics and system monitoring
- ✅ **Real-time dashboard** with Server-Sent Events for live tailing
- ✅ **Comprehensive request audit** logging

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


