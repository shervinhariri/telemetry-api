# Telemetry API — v0.9.0-golden

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
        --name telapi shvin/telemetry-api:v0.9.0-golden

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

## 🏗️ Two-Container Deployment Policy

This project follows a strict two-container deployment model to ensure stability and enable safe feature development:

### **:80 = Golden Image (Stable Release)**
- **Purpose**: Production deployments, stable releases
- **Image**: `shvin/telemetry-api:v0.9.0-golden` (latest golden tag)
- **Port**: 80
- **Policy**: Never change unless approved for release
- **Use Case**: Production environments, demos, stable testing

### **:8080 = Dev Image (Feature Branch)**
- **Purpose**: Feature development, testing, validation
- **Image**: `telemetry-api:dev` (or PR-specific tags)
- **Port**: 8080 (API) + 8081/udp (UDP Head)
- **Policy**: Changes frequently during development
- **Use Case**: Feature testing, development, CI/CD validation

### **Promotion Path: Dev → Golden (Never Reverse)**
```bash
# Development workflow:
# 1. Test features on :8080 (dev container)
# 2. Validate with e2e tests
# 3. Promote dev image to golden tag
# 4. Update production :80 to use new golden image
```

## Quick Start

### 🏆 Golden Release (Recommended for Production)

For production deployments, use the golden release which has been thoroughly tested and validated:

```bash
# PROD (port 80) — golden image
docker rm -f telemetry-prod 2>/dev/null || true
docker run -d --name telemetry-prod -p 80:80 \
  -e TELEMETRY_SEED_KEYS="TEST_ADMIN_KEY,DEV_ADMIN_KEY_5a8f9ffdc3" \
  shvin/telemetry-api:v0.9.0-golden

# Verify the golden release
curl -s http://localhost/v1/health | jq
curl -s http://localhost/v1/version | jq
```

### 🧪 Dev Container (Feature Testing)

For feature development and testing:

```bash
# DEV (port 8080) — branch image under test
DEV_TAG=telemetry-api:dev  # or PR-specific tag
docker rm -f telemetry-dev 2>/dev/null || true
docker run -d --name telemetry-dev -p 8080:80 -p 8081:8081/udp \
  -e TELEMETRY_SEED_KEYS="TEST_ADMIN_KEY,DEV_ADMIN_KEY_5a8f9ffdc3" \
  -e FEATURE_UDP_HEAD=true \
  $DEV_TAG

# Verify they're different
curl -s http://localhost:80/v1/version && echo
curl -s http://localhost:8080/v1/version && echo
```

**Golden Release Benefits:**
- ✅ Thoroughly tested and validated
- ✅ SBOM available for security audit
- ✅ Checksums verified for integrity
```

## 🏢 Multi-Tenancy (v0.8.11)

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
  --name telemetry-api shvin/telemetry-api:0.8.11

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
    image: shvin/telemetry-api:0.8.11
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
        image: shvin/telemetry-api:0.8.11
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

This release: shvin/telemetry-api:0.8.11

Previous golden: shvin/telemetry-api:0.8.2-golden

## Versioning

Semantic-ish minor bumps for UI/bugfix releases

Keep VERSION in repo aligned with Docker tag and /v1/version

## 📋 Changelog

### v0.8.11 (Current)
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


