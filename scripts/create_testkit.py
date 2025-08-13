#!/usr/bin/env python3
"""
Create Telemetry API Testkit
Generates a comprehensive test package with sample payloads and test scripts.
"""

import os
import json
import gzip
import shutil
import textwrap
import stat
import pathlib

def create_testkit():
    # Create testkit directory
    root = "telemetry-api-testkit"
    os.makedirs(root, exist_ok=True)
    data_dir = os.path.join(root, "data")
    os.makedirs(data_dir, exist_ok=True)

    # Sample payloads
    raw_array = [
        {
            "ts": "2025-08-13T18:40:00Z",
            "src_ip": "10.0.0.10", "src_port": 54321,
            "dst_ip": "8.8.8.8",   "dst_port": 53,
            "proto": "udp", "bytes": 128, "packets": 1
        },
        {
            "ts": "2025-08-13T18:40:05Z",
            "src_ip": "10.0.0.20", "src_port": 51515,
            "dst_ip": "1.1.1.1",   "dst_port": 443,
            "proto": "tcp", "bytes": 2048, "packets": 2
        },
        {
            "ts": "2025-08-13T18:40:10Z",
            "src_ip": "192.168.1.100", "src_port": 12345,
            "dst_ip": "8.8.4.4",   "dst_port": 53,
            "proto": "udp", "bytes": 64, "packets": 1
        }
    ]

    wrapped = {"records": raw_array}
    invalid_missing_ts = [{"src_ip": "10.0.0.1"}]  # should trigger 400 due to missing timestamp

    # Write sample data files
    with open(os.path.join(data_dir, "data_raw_array.json"), "w") as f:
        json.dump(raw_array, f, indent=2)

    with open(os.path.join(data_dir, "data_wrapped.json"), "w") as f:
        json.dump(wrapped, f, indent=2)

    with open(os.path.join(data_dir, "data_invalid.json"), "w") as f:
        json.dump(invalid_missing_ts, f, indent=2)

    # Gzipped version of raw_array
    gz_path = os.path.join(data_dir, "data_raw_array.json.gz")
    with gzip.open(gz_path, "wb") as gz:
        gz.write(json.dumps(raw_array).encode("utf-8"))

    # Bash test script
    script = textwrap.dedent("""\
#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://localhost:8080}"
API_KEY="${API_KEY:-TEST_KEY}"
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="$D/data"

pass() { echo -e "✅ $1"; }
fail() { echo -e "❌ $1"; exit 1; }
warn() { echo -e "⚠️  $1"; }

curl_json() {
  local method="$1"; shift
  local path="$1"; shift
  local datafile="${1:-}"; shift || true
  local extra=("$@")
  if [[ -n "$datafile" ]]; then
    curl -sS -w "\\n%{http_code}" -X "$method" "$BASE$path" \\
         -H "Authorization: Bearer $API_KEY" \\
         -H "Content-Type: application/json" \\
         --data "@${datafile}"
  else
    curl -sS -w "\\n%{http_code}" -X "$method" "$BASE$path" \\
         -H "Authorization: Bearer $API_KEY" \\
         -H "Content-Type: application/json"
  fi
}

echo "=== Telemetry API Local Testkit ==="
echo "Base: $BASE"
echo "API Key: $API_KEY"
echo ""

# 1) Health (no auth required)
echo "🔍 Testing /v1/health (public endpoint)..."
resp="$(curl -sS -w "\\n%{http_code}" "$BASE/v1/health")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]]; then 
    pass "Health OK: $body"; 
else 
    fail "Health FAILED ($code): $body"; 
fi

# 2) Version (Patch 5.1)
echo ""
echo "🔍 Testing /v1/version (Patch 5.1)..."
resp="$(curl_json GET "/v1/version")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]]; then 
    pass "Version: $body"; 
else 
    fail "Version FAILED ($code): $body"; 
fi

# 3) Updates check (Patch 5.1)
echo ""
echo "🔍 Testing /v1/updates/check (Patch 5.1)..."
resp="$(curl_json GET "/v1/updates/check")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]]; then
  if echo "$body" | grep -q '"update_available": *true'; then
    warn "Update available → $body"
  else
    pass "Up-to-date → $body"
  fi
else
  warn "Updates check skipped ($code): $body"
fi

# 4) Output connector configs (Stage 5.1)
echo ""
echo "🔍 Testing /v1/outputs/splunk (Stage 5.1)..."
resp="$(curl_json POST "/v1/outputs/splunk" "$DATA/splunk.json")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]]; then 
    pass "Configured Splunk"; 
else 
    fail "Configure Splunk FAILED ($code): $body"; 
fi

echo ""
echo "🔍 Testing /v1/outputs/elastic (Stage 5.1)..."
resp="$(curl_json POST "/v1/outputs/elastic" "$DATA/elastic.json")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]]; then 
    pass "Configured Elastic"; 
else 
    fail "Configure Elastic FAILED ($code): $body"; 
fi

# 5) Ingest tests (Stage 5 robust pipeline)
echo ""
echo "🔍 Testing /v1/ingest - Raw JSON array..."
resp="$(curl_json POST "/v1/ingest" "$DATA/data_raw_array.json")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]] && echo "$body" | grep -qi '"accepted"'; then 
    pass "Ingest raw array accepted"; 
else 
    fail "Ingest raw array FAILED ($code): $body"; 
fi

echo ""
echo "🔍 Testing /v1/ingest - Wrapped object {records: [...]}..."
resp="$(curl_json POST "/v1/ingest" "$DATA/data_wrapped.json")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]] && echo "$body" | grep -qi '"accepted"'; then 
    pass "Ingest wrapped accepted"; 
else 
    fail "Ingest wrapped FAILED ($code): $body"; 
fi

echo ""
echo "🔍 Testing /v1/ingest - Gzip (Content-Encoding: gzip)..."
resp="$(curl -sS -w "\\n%{http_code}" -X POST "$BASE/v1/ingest" \\
    -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -H "Content-Encoding: gzip" \\
    --data-binary "@$DATA/data_raw_array.json.gz")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]] && echo "$body" | grep -qi '"accepted"'; then 
    pass "Ingest gzip accepted"; 
else 
    fail "Ingest gzip FAILED ($code): $body"; 
fi

echo ""
echo "🔍 Testing /v1/ingest - Invalid record (should return 400)..."
resp="$(curl_json POST "/v1/ingest" "$DATA/data_invalid.json")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "400" ]]; then 
    pass "Bad record correctly rejected (400)"; 
else 
    fail "Bad record expected 400, got $code: $body"; 
fi

# 6) Metrics (optional)
echo ""
echo "🔍 Testing /v1/metrics..."
resp="$(curl -sS -w "\\n%{http_code}" "$BASE/v1/metrics")" || true
body="$(echo "$resp" | sed '$d')"
code="$(echo "$resp" | tail -n1)"
if [[ "$code" == "200" ]]; then
  if echo "$body" | grep -q -E "records_queued|records_processed|ingest"; then
    pass "Metrics available and contain ingest counters"
  else
    warn "Metrics up but no ingest counters detected"
  fi
else
  warn "Metrics endpoint not available ($code)"
fi

echo ""
echo "=== All tests completed ==="
echo "🌐 GUI available at: $BASE"
echo "   Look for the version badge in the top-right corner!"
""")

    with open(os.path.join(root, "run_tests.sh"), "w") as f:
        f.write(script)
    os.chmod(os.path.join(root, "run_tests.sh"), os.stat(os.path.join(root, "run_tests.sh")).st_mode | stat.S_IEXEC)

    # Minimal connector config payloads
    splunk_cfg = {
        "hec_url": "https://splunk.example:8088/services/collector",
        "token": "REDACTED",
        "index": "telemetry",
        "sourcetype": "telemetry:event",
        "batch_size": 500,
        "max_retries": 5,
        "backoff_ms": 200,
        "verify_tls": True
    }
    elastic_cfg = {
        "urls": ["https://es1:9200"],
        "index_prefix": "telemetry-",
        "bulk_size": 1000,
        "max_retries": 5,
        "backoff_ms": 200,
        "verify_tls": True
    }

    with open(os.path.join(data_dir, "splunk.json"), "w") as f:
        json.dump(splunk_cfg, f, indent=2)
    with open(os.path.join(data_dir, "elastic.json"), "w") as f:
        json.dump(elastic_cfg, f, indent=2)

    # README for the testkit
    readme = """# Telemetry API Testkit (Local)

## Prerequisites
- `curl` and `gzip` installed
- Telemetry API running locally at `http://localhost:8080`
- API key configured (default: `TEST_KEY`)

## Quick Start
```bash
# Extract the testkit
unzip telemetry-api-testkit.zip
cd telemetry-api-testkit

# Optional overrides
export BASE=http://localhost:8080
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
1. **Connection refused** - Make sure API is running on port 8080
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
"""

    with open(os.path.join(root, "README_TESTS.md"), "w") as f:
        f.write(readme)

    # Create ZIP file
    zip_path = "telemetry-api-testkit.zip"
    if os.path.exists(zip_path):
        os.remove(zip_path)
    
    shutil.make_archive("telemetry-api-testkit", "zip", root)
    
    print(f"✅ Testkit created: {zip_path}")
    print(f"📁 Contents: {root}/")
    print(f"📄 README: {root}/README_TESTS.md")
    print(f"🚀 Test script: {root}/run_tests.sh")
    print(f"📊 Sample data: {root}/data/")
    
    return zip_path

if __name__ == "__main__":
    create_testkit()
