# Stage 3 - Contract Alignment Deliverables Checklist

## ✅ Endpoint Parity with Step 2

- [x] `GET /v1/health` - Health check with X-API-Version header
- [x] `POST /v1/ingest` - Batch upload with 5MB/10k record limits
- [x] `POST /v1/lookup` - Single IP enrichment
- [x] `POST /v1/outputs/splunk` - Splunk HEC configuration
- [x] `POST /v1/outputs/elastic` - Elasticsearch configuration
- [x] `POST /v1/alerts/rules` - Alert rules configuration (placeholder)
- [x] `GET /v1/metrics` - Prometheus metrics with basic auth
- [x] `GET /v1/version` - Version info with metadata
- [x] `GET /v1/schema` - Schema information endpoint

## ✅ X-API-Version & /v1/version

- [x] X-API-Version header middleware implemented
- [x] /v1/version endpoint returns version, git_tag, image_digest
- [x] All endpoints include X-API-Version header

## ✅ JSON Schemas + /v1/schema

- [x] `schemas/zeek.conn.v1.schema.json` - Zeek connection format
- [x] `schemas/flows.v1.schema.json` - Network flows format
- [x] `schemas/enriched.v1.schema.json` - Enriched output format
- [x] `/v1/schema` endpoint returns schema references
- [x] Schema validation script (`tests/validate_schemas.py`)

## ✅ Tests: Unit + Integration + Schema Validation

- [x] Unit tests for authentication (`tests/test_api.py`)
- [x] Unit tests for limits (5MB payload, 10k records)
- [x] Unit tests for risk scoring (0-100 range)
- [x] Integration tests for all endpoints
- [x] Schema validation for sample data
- [x] CI integration with GitHub Actions

## ✅ Dead-letter Folder for Failed Outputs

- [x] `ops/deadletter/` directory structure
- [x] Deadletter handling in API (`write_deadletter()` function)
- [x] Timestamped files with UUID for uniqueness
- [x] JSONL format with reason and payload

## ✅ Rate Limit Envs & Docs (Contract vs Prod)

- [x] `RATE_LIMIT_INGEST_RPM` (default: 120, contract: 600)
- [x] `RATE_LIMIT_DEFAULT_RPM` (default: 600, contract: 600)
- [x] Updated Caddyfile with environment-driven config
- [x] Documentation in README.md and DEPLOYMENT.md
- [x] Examples for raising limits in trusted environments

## ✅ README & DEPLOYMENT.md Updated

- [x] Production deployment steps (3 steps)
- [x] Validation commands
- [x] Outputs configuration
- [x] Environment variables table
- [x] Limits and error documentation
- [x] Rate limiting configuration
- [x] API endpoints documentation

## ✅ CI Updated for Tests and Tag Builds

- [x] GitHub Actions enhanced with test job
- [x] Tests run on pull requests
- [x] Schema validation in CI pipeline
- [x] Docker builds on version tags
- [x] Test dependencies added to requirements.txt

## ✅ Production Deployment Bundle

- [x] `docker-compose.yml` - Production services
- [x] `Caddyfile` - HTTPS reverse proxy with rate limiting
- [x] `.env.example` - Complete environment template
- [x] `scripts/bootstrap.sh` - Server setup
- [x] `scripts/deploy.sh` - Deployment automation
- [x] `scripts/update.sh` - Update automation
- [x] `scripts/logs.sh` - Log viewing
- [x] `scripts/test_health.sh` - Health testing
- [x] `scripts/test_ingest.sh` - Ingest testing
- [x] `scripts/configure_splunk.sh` - Splunk setup
- [x] `scripts/configure_elastic.sh` - Elasticsearch setup
- [x] `scripts/run_tests.sh` - Local test runner

## ✅ Security & Operations

- [x] UFW firewall configuration (ports 22, 80, 443)
- [x] Fail2ban configuration for brute force protection
- [x] Logrotate configuration for Caddy logs
- [x] Basic auth for metrics endpoint
- [x] CORS headers for cross-origin requests
- [x] Security headers (X-Content-Type-Options, etc.)

## ✅ Sample Data & Validation

- [x] `samples/zeek_conn.json` - Zeek connection sample
- [x] `samples/flows_v1.json` - Network flows sample
- [x] Schema validation for both sample formats
- [x] Test scripts using sample data

## 🎯 Ready for Production

All deliverables are complete and the Stage 3 deployment bundle is:

- ✅ **Minimal** - Only essential components included
- ✅ **Testable** - Comprehensive test suite with CI integration
- ✅ **Shippable** - Production-ready with security and monitoring
- ✅ **Contract Compliant** - Aligned with Step 1-2 specifications

## 🚀 Next Steps

1. **Create PR**: `git push origin stage3-contract-alignment`
2. **Review**: Ensure all tests pass in CI
3. **Merge**: Deploy to production environment
4. **Monitor**: Use provided scripts for operations

The Stage 3 contract alignment is complete and ready for production deployment!
