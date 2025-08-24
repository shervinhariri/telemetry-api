# Telemetry API — v0.8.9

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
        --name telapi shvin/telemetry-api:0.8.9

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

### 🏆 Golden Release (Recommended for Production)

For production deployments, use the golden release which has been thoroughly tested and validated:

```bash
# Pull and run the golden release
docker pull shvin/telemetry-api:0.8.9-golden
docker run -d -p 80:80 \
  -e API_KEY=YOUR_API_KEY \
  --name telemetry-api-golden \
  shvin/telemetry-api:0.8.9-golden

# Verify the golden release
curl -s http://localhost/v1/health | jq
```

**Golden Release Benefits:**
- ✅ Thoroughly tested and validated
- ✅ SBOM available for security audit
- ✅ Checksums verified for integrity
- ✅ Release notes and changelog included
- ✅ Immutable tag for reproducible deployments

**Rollback to Golden:**
```bash
# Stop current container
docker stop telemetry-api-current

# Pull and run golden release
docker pull shvin/telemetry-api:0.8.9-golden
docker run -d -p 80:80 \
  -e API_KEY=YOUR_API_KEY \
  --name telemetry-api-golden \
  shvin/telemetry-api:0.8.9-golden

# Verify rollback
curl -s http://localhost/v1/health | jq
```

**Release Assets:**
- [Release Page](https://github.com/shervinhariri/telemetry-api/releases/tag/v0.8.9)
- [SBOM (SPDX JSON)](https://github.com/shervinhariri/telemetry-api/releases/download/v0.8.9/sbom-0.8.9.spdx.json)
- [Checksums](https://github.com/shervinhariri/telemetry-api/releases/download/v0.8.9/checksums-0.8.9.txt)

### Option 1: All-in-One Container (Development)

A single container that includes the API, NetFlow collector, and mapper:

```bash
# Build and start the all-in-one container
docker compose up -d telemetry-allinone

# Verify everything is working
./scripts/verify_allinone.sh

# Generate test NetFlow data
python3 scripts/generate_test_netflow.py --count 10 --flows 5

# Check metrics
curl -s -H "Authorization: Bearer TEST_KEY" "http://localhost/v1/metrics?window=300" | jq
```

**Features:**
- ✅ API/GUI on port 80
- ✅ NetFlow/IPFIX collector on port 2055/udp
- ✅ Automatic goflow2 → mapper → API pipeline
- ✅ Multi-architecture support (AMD64/ARM64)
- ✅ Single container deployment

### Option 2: Standard API Container

```bash
# Single container with MaxMind/TI data
docker run -d -p 80:80 \
  -e API_KEY=TEST_KEY \
  -e GEOIP_DB_CITY=/data/GeoLite2-City.mmdb \
  -e GEOIP_DB_ASN=/data/GeoLite2-ASN.mmdb \
  -e THREATLIST_CSV=/data/threats.csv \
  -v $PWD/data:/data:ro \
  --name telemetry-api shvin/telemetry-api:0.8.9

# Open dashboard
open http://localhost

Paste your API key in the UI

Use API tab to send ingest / lookup

Use Logs tab for live logs

Note: Browsers do not allow custom headers in EventSource. The UI uses ?key= for SSE; the backend accepts it only for the /v1/logs/stream endpoint.

# Test ingest
curl -s -X POST http://localhost/v1/ingest/zeek \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data @samples/zeek_conn_small.json | jq
```

## Configuration (env vars)

| Variable | Purpose | Default |
|---|---|---|
| `TELEMETRY_SEED_KEYS` | Seed comma‑separated admin API keys on startup | *(none)* |
| `API_KEY` | (Legacy single key) if not using `TELEMETRY_SEED_KEYS` | `TEST_KEY` |
| `FEATURE_UDP_HEAD` | Enable experimental UDP head | `false` |
| `ENRICH_ENABLE_{GEOIP,ASN,TI}` | Toggle enrichments | `true` |
| `RETENTION_DAYS` | Data retention window | `7` |

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

This repository maintains a golden tag for the stable build of 0.8.9:

- Git tag: `v0.8.9-golden`
- Docker image: `shvin/telemetry-api:0.8.9-golden`

Rollback instructions:

```bash
git fetch --tags
git checkout v0.8.9-golden

docker pull shvin/telemetry-api:0.8.9-golden
docker rm -f telemetry-api || true
docker run -d -p 80:80 \
  -v $PWD/telemetry.db:/app/telemetry.db \
  --name telemetry-api \
  shvin/telemetry-api:0.8.9-golden
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
  --name telemetry-api-demo shvin/telemetry-api:0.8.9

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

## 🏢 Multi-Tenancy (v0.8.9)

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
  --name telemetry-api shvin/telemetry-api:0.8.9

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

## 🏢 Multi-Tenancy (v0.8.9)

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
  --name telemetry-api shvin/telemetry-api:0.8.9

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

# Build and run with Docker Compose (includes NetFlow collector)
docker compose up -d

# Or build and run standalone
docker build -t telemetry-api:local .
docker run -d -p 80:80 -e API_KEY=TEST_KEY --name telemetry-api telemetry-api:local

# Test
curl -s http://localhost/v1/health | jq
```

### NetFlow Collection
```bash
# Start NetFlow collector
docker compose up -d collector

# Test with sample data
python3 scripts/generate_test_netflow.py --count 5 --flows 3

# Monitor flow data
docker compose logs -f collector
```

### Testing
```bash
# Health check
./scripts/test_health.sh

# Ingest test
./scripts/test_ingest.sh

# Full test suite
./scripts/run_tests.sh

# All-in-one verification (recommended)
export API_KEY=TEST_KEY
bash scripts/verify_allinone.sh
```

### Continuous Integration

The project uses GitHub Actions for automated testing and builds:

- **Scenario Tests**: Comprehensive end-to-end testing with real API calls
- **Unit Tests**: Fast unit tests using pytest
- **Docker Builds**: Multi-architecture container builds (AMD64/ARM64)
- **Registry Mirrors**: Images pushed to Docker Hub (public) and GHCR (private)

**Test failures fail the build** - no `|| true` workarounds. The CI pipeline includes:

1. **Container startup** with 80-second health check timeout
2. **Python dependency caching** for faster runs  
3. **Unit tests** that must pass (`pytest -q`)
4. **Scenario tests** that verify API behavior and return proper exit codes
5. **Automatic log collection** on failures for debugging

View build status: ![Build](https://github.com/shervinhariri/telemetry-api/actions/workflows/docker.yml/badge.svg)

### Phase B Tests (Admission Control & Metrics)
```bash
# Run comprehensive admission control and metrics tests
make test-phase-b

# Or run directly with custom settings
API=http://localhost KEY=TEST_KEY ADMIN_KEY=ADMIN_SOURCES_TEST bash scripts/test_phase_b.sh

# Optional: Enable FIFO pressure testing
B4_FIFO_TEST=1 make test-phase-b

# Simplified metrics test (recommended for basic verification)
./scripts/test_phase_b_simple.sh
```

**Note**: 
- If `ADMISSION_HTTP_ENABLED=false`, enable it in your compose/env and restart before running tests
- The test creates temporary sources with different security profiles to validate admission control
- Metrics infrastructure is fully functional and ready for production monitoring

### Runtime Feature Flags & Rollback

The system includes comprehensive runtime feature flags for admission control management:

**Feature Flags:**
- `ADMISSION_HTTP_ENABLED`: Enable/disable HTTP admission control
- `ADMISSION_UDP_ENABLED`: Enable/disable UDP admission control (future)
- `ADMISSION_LOG_ONLY`: Log blocks but allow requests (safe rollout)
- `ADMISSION_FAIL_OPEN`: Allow requests on admission control errors (emergency)
- `ADMISSION_COMPAT_ALLOW_EMPTY_IPS`: Treat empty IP lists as allow-any (legacy)
- `ADMISSION_BLOCK_ON_EXCEED_DEFAULT`: Default behavior for rate limit violations

**Safe Defaults:** All admission control features are disabled by default to prevent surprise outages.

**Runtime Management:**
```bash
# View current flags
make flags-show

# Enable HTTP admission control
make flags-http-on

# Enable LOG_ONLY mode (safe rollout)
make flags-logonly-on

# Disable admission control
make flags-http-off
```

**Emergency Rollback Sequence:**
1. `make flags-logonly-on` - No user-visible errors, metrics still count
2. `make flags-http-off` - Completely disable admission control
3. Restart with `ADMISSION_HTTP_ENABLED=false` in compose for permanent fix

**Production Rollout:**
1. Deploy with flags disabled
2. Enable LOG_ONLY in staging, monitor metrics
3. Enable full admission control in staging
4. Roll out to production with LOG_ONLY first
5. Switch to full enforcement once stable

**UDP Admission Control (Phase B2):**
The system now includes UDP admission control for complete pipeline security:

- **IP-based filtering**: Only approved exporter IPs can send NetFlow/IPFIX data
- **Rate limiting**: Per-source EPS limits with configurable enforcement
- **Sources cache**: Efficient in-memory cache for IP matching (refreshes every 30s)
- **Metrics integration**: All UDP blocks are recorded in Prometheus metrics
- **Feature flag support**: Respects all admission control feature flags

**Testing UDP Admission Control:**
```bash
# Enable UDP admission control
export ADMISSION_UDP_ENABLED=true

# Test with dummy packets
python3 scripts/send_ipfix_dummy.py --host localhost --port 2055 --count 10

# Run comprehensive UDP tests
HAS_UDP_TEST=1 make test-phase-b
```

**Kernel Allowlist (Phase C1):**
The system includes kernel-level UDP filtering using nftables for maximum security:

- **Hardware-level filtering**: Unauthorized packets are dropped at the kernel level
- **Automatic synchronization**: nftables sets are synced from enabled sources
- **IPv4/IPv6 support**: Both address families are supported
- **Zero CPU overhead**: Kernel filtering is extremely efficient

**Setup and Usage:**
```bash
# Initial setup (one-time, requires sudo)
make firewall-setup

# Sync allowlist from sources to nftables
make firewall-sync

# Check allowlist status
make firewall-status

# View current nftables set
make firewall-show

# Test kernel allowlist functionality
make test-phase-c1
```

**Rollback:**
```bash
# Clear nftables set
sudo nft flush set inet telemetry exporters

# Remove rules (if needed)
sudo nft delete rule inet telemetry input udp dport 2055 drop
```

**Current Status:**
- ✅ Core admission control infrastructure implemented
- ✅ Metrics infrastructure fully functional
- ✅ UDP metrics endpoint working
- ✅ Environment-based configuration working
- ✅ UDP admission control implemented (Phase B2)
- ✅ Sources cache for efficient IP matching
- ✅ Kernel allowlist API infrastructure ready (Phase C1)
- ⚠️ Runtime feature flags API needs debugging (can be added later)
- ✅ Ready for production deployment with environment-based flags

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
    image: shvin/telemetry-api:0.8.9
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
        image: shvin/telemetry-api:0.8.9
        ports:
        - containerPort: 80
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: telemetry-secrets
              key: api-key
```

## 📋 Releases & Tags

-- Images are tagged :latest, :0.x.y, and :golden for stable rollback.

This release: shvin/telemetry-api:0.8.9

Previous golden: shvin/telemetry-api:0.8.2-golden

## Versioning

Semantic-ish minor bumps for UI/bugfix releases

Keep VERSION in repo aligned with Docker tag and /v1/version

## 📋 Changelog

### v0.8.9 (Current)
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

## Known Limitations

MVP focuses on NetFlow/IPFIX JSON & Zeek JSON (Phase 2 adds PCAP headers, JA3, basic ML)

Splunk HEC & Elastic bulk JSON outputs (Phase 2: QRadar, Datadog)

SSE in browsers requires ?key= on /v1/logs/stream as described above.

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


