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

## What It Tests

### Patch 5.1 Features
- **`/v1/health`** - Public health check (no auth required)
- **`/v1/version`** - Version information and metadata
- **`/v1/updates/check`** - Docker Hub update availability check

### Stage 5.1 Output Connectors
- **`/v1/outputs/splunk`** - Splunk HEC configuration
- **`/v1/outputs/elastic`** - Elasticsearch configuration

### Stage 5 Robust Ingest Pipeline
- **Raw JSON array** - Direct array ingestion
- **Wrapped object** - `{"records": [...]}` format
- **Gzip compression** - `Content-Encoding: gzip` support
- **Error handling** - Invalid payload returns 400 (not 500)
- **`/v1/metrics`** - Queue depth and processing metrics

## Sample Data Files

### Valid Payloads
- `data_raw_array.json` - Three example events with timestamps, IPs, ports, etc.
- `data_wrapped.json` - Same events wrapped in `{"records": [...]}` format
- `data_raw_array.json.gz` - Gzipped version of raw array

### Invalid Payload
- `data_invalid.json` - Missing timestamp to trigger 400 error

### Configuration Files
- `splunk.json` - Splunk HEC configuration
- `elastic.json` - Elasticsearch configuration

## Expected Results

### ✅ Success Indicators
- "Health OK" - API is running and accessible
- "Version" - Patch 5.1 version endpoint working
- "Ingest raw array accepted" - Array crash fix working
- "Ingest gzip accepted" - Gzip decode working
- "Bad record correctly rejected (400)" - Proper error handling

### ⚠️ Warnings (Normal)
- "Updates check skipped" - If Docker Hub is unreachable
- "Metrics endpoint not available" - If metrics not implemented yet

### ❌ Failure Indicators
- "Health FAILED" - API not running or wrong port
- "Ingest raw array FAILED" - Array handling not fixed
- "Ingest gzip FAILED" - Gzip support not working

## Troubleshooting

### Common Issues
1. **Connection refused** - Make sure API is running on port 80
2. **401 Unauthorized** - Check API_KEY environment variable
3. **404 Not Found** - Verify endpoint paths are correct
4. **500 Internal Server Error** - Check server logs for details

### Server Logs
If tests fail, check your telemetry-api container logs:
```bash
docker logs telemetry-api
```

## API Contract Compliance

This testkit validates compliance with the Step-2 API contract:
- Endpoint paths and methods
- Authentication requirements
- Request/response formats
- Error status codes (4xx vs 5xx)
- Content encoding support
- Size and rate limits
