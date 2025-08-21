# Telemetry API Testkit (Local)

## Prerequisites
- `curl` and `gzip` installed
- Telemetry API running locally at `http://localhost`
- API key configured (default: `TEST_KEY`)

## Quick Start
```bash
# Extract the testkit
unzip telemetry-api-testkit.zip
cd telemetry-api-testkit

# Optional overrides
export BASE=http://localhost
export API_KEY=TEST_KEY

# Run all tests
./run_tests.sh
```

## All-in-One Container Verification

The primary verification script is `scripts/verify_allinone.sh` which provides comprehensive testing of the complete telemetry pipeline.

### Usage
```bash
# Basic usage with defaults
export API_KEY=TEST_KEY
bash scripts/verify_allinone.sh

# Custom configuration
export API_KEY=your-api-key
export BASE_URL=http://your-host:port
export VERSION_FILE=path/to/VERSION
bash scripts/verify_allinone.sh
```

### What It Tests

#### Container Management
- **Container Status**: Checks if container is running, starts if needed
- **Port Exposure**: Verifies TCP/80 (API/GUI) and UDP/2055 (NetFlow) are listening

#### API Endpoints
- **`/v1/health`** - Public health check (no auth required)
- **`/v1/version`** - Version information (reads from VERSION file)
- **`/v1/metrics`** - Processing metrics and queue depth

#### NetFlow Pipeline
- **Data Generation**: Uses `scripts/generate_test_netflow.py` to create test data
- **Ingestion Verification**: Confirms metrics increase after data generation
- **Component Logs**: Checks goflow2, mapper, and API server logs
- **Success Indicators**: Looks for successful ingest operations in logs

#### UI Accessibility
- **Web Interface**: Verifies UI is accessible on port 80

### Expected Results

#### ✅ Success Indicators
- "Container is running" - Docker container operational
- "Health endpoint responding (HTTP 200)" - API accessible
- "Version matches expected: X.X.X" - Version from VERSION file
- "NetFlow records were processed successfully" - Pipeline working
- "EPS is non-zero" - Events per second being calculated
- "Mapper successfully sent data to API" - Internal pipeline functional

#### ❌ Failure Indicators
- "Container not running" - Docker issues
- "Health endpoint failed" - API not accessible
- "Version mismatch" - Version file vs API mismatch
- "No NetFlow records were processed" - Pipeline broken
- "No successful ingest operations found" - Internal communication issues

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | `TEST_KEY` | API key for authenticated endpoints |
| `BASE_URL` | `http://localhost` | Base URL for API endpoints |
| `VERSION_FILE` | `VERSION` | Path to version file |

### Troubleshooting

#### Common Issues
1. **Container not starting** - Check Docker and docker-compose
2. **API not responding** - Verify container is running and ports are exposed
3. **Version mismatch** - Ensure VERSION file exists and contains correct version
4. **NetFlow not processing** - Check UDP port 2055 and mapper logs
5. **Authentication failures** - Verify API_KEY environment variable

#### Debug Commands
```bash
# Check container status
docker compose ps

# View container logs
docker compose logs api-core

# Check port exposure
netstat -an | grep :80
netstat -an | grep :2055

# Test API directly
curl -s http://localhost/v1/health
curl -s http://localhost/v1/version

# Generate test data manually
python3 scripts/generate_test_netflow.py --count 5 --flows 3
```

## Legacy Test Scripts

The following scripts are still available for specific testing scenarios:

### API Testing
- **`scripts/test_api.sh`** - Basic API endpoint testing
- **`scripts/run_tests.sh`** - Comprehensive API test suite

### Component Testing
- **`scripts/test_netflow.sh`** - NetFlow-specific testing
- **`scripts/verify_mapper.sh`** - Mapper integration testing

### Feature Testing
- **`scripts/test_sources_backend.sh`** - Sources API testing
- **`scripts/test_sources_ui.sh`** - Sources UI testing
- **`scripts/test_phase_*.sh`** - Phase-specific feature testing

## API Contract Compliance

This testkit validates compliance with the API contract:
- Endpoint paths and methods
- Authentication requirements
- Request/response formats
- Error status codes (4xx vs 5xx)
- Content encoding support
- Size and rate limits
- Version management (VERSION file integration)
