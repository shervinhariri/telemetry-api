# 🚀 Tomorrow Morning Task: Stage 3 Local Validation (v0.3.0)

## Goal
Run the production bundle locally (Docker), validate endpoints against the Stage 1–2 contract, and ingest real sample logs generated on the fly.

## Repository & Tag
- **Repo**: `shervinhariri/telemetry-api`
- **Tag**: `v0.3.0`
- **Branch**: `stage3-contract-alignment`

## 📋 Execution Steps

**Execute commands exactly as provided, in order. If a step fails, fix and re‑run.**

---

### 0) Prep Workspace
Open the repo folder in Cursor.

Create/refresh .env from example and fill the few required values:

```bash
git fetch --all --tags
git checkout v0.3.0

cp -n .env.example .env

# Minimal env to run locally; edit as needed
# Required: API key for tests, MaxMind paths only if you enabled GeoIP locally.
sed -i.bak 's/^API_KEY=.*/API_KEY=TEST_KEY/' .env || gsed -i 's/^API_KEY=.*/API_KEY=TEST_KEY/' .env

# Rate limits (prod-safe defaults)
export RATE_LIMIT_INGEST_RPM=${RATE_LIMIT_INGEST_RPM:-120}
export RATE_LIMIT_DEFAULT_RPM=${RATE_LIMIT_DEFAULT_RPM:-600}
```

---

### 1) Build & Launch Services
```bash
docker compose pull || true
docker compose build --pull
docker compose up -d

# Show status + health
docker compose ps
./scripts/test_health.sh
```

**Pass criteria**: GET /v1/health returns 200 and response includes X-API-Version.

---

### 2) Run the Test Suite + Schema Validation
```bash
./scripts/run_tests.sh
```

**Pass criteria**: All unit/integration tests pass; schema validation completes with no errors.

---

### 3) Generate Sample Logs Locally (flows + zeek.conn)
Create small yet realistic test payloads you can reuse:

```bash
mkdir -p samples/generated

cat > samples/generated/flows_sample.json <<'JSON'
{
  "collector_id": "test-flows-1",
  "format": "flows.v1",
  "records": [
    {
      "ts": 1723351200.456,
      "src_ip": "10.0.1.10",
      "src_port": 51544,
      "dst_ip": "93.184.216.34",
      "dst_port": 443,
      "protocol": "tcp",
      "bytes": 12345,
      "packets": 18
    },
    {
      "ts": 1723351260.789,
      "src_ip": "10.0.1.11",
      "src_port": 53022,
      "dst_ip": "8.8.8.8",
      "dst_port": 53,
      "protocol": "udp",
      "bytes": 420,
      "packets": 2
    }
  ]
}
JSON

cat > samples/generated/zeek_conn_sample.json <<'JSON'
{
  "collector_id": "test-zeek-1",
  "format": "zeek.conn.v1",
  "records": [
    {
      "ts": 1723351320.123,
      "uid": "Ck1Qev1Y4pZqfJm",
      "id_orig_h": "10.0.1.12",
      "id_orig_p": 58742,
      "id_resp_h": "1.1.1.1",
      "id_resp_p": 53,
      "proto": "udp",
      "service": "dns",
      "orig_bytes": 77,
      "resp_bytes": 256,
      "duration": 0.015
    }
  ]
}
JSON
```

---

### 4) Ingest Tests (curl + scripts)

#### A) Direct curl (flows):
```bash
curl -i -X POST http://localhost:8080/v1/ingest \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data @samples/generated/flows_sample.json
```

#### B) Direct curl (zeek.conn):
```bash
curl -i -X POST http://localhost:8080/v1/ingest \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data @samples/generated/zeek_conn_sample.json
```

#### C) With helper scripts:
```bash
./scripts/test_ingest.sh
```

**Pass criteria**: 2xx status; response indicates accepted records; no errors in container logs:

```bash
./scripts/logs.sh | tail -n +1
```

---

### 5) Contract Endpoints Spot‑check
```bash
# Version metadata
curl -s -i -H "Authorization: Bearer TEST_KEY" http://localhost:8080/v1/version

# Schema
curl -s -H "Authorization: Bearer TEST_KEY" http://localhost:8080/v1/schema | jq '.enriched_schema,.input_schemas'

# Single lookup
curl -s -X POST http://localhost:8080/v1/lookup \
  -H "Authorization: Bearer TEST_KEY" -H "Content-Type: application/json" \
  --data '{"ip": "8.8.8.8"}' | jq
```

**Pass criteria**: All return 200 with expected fields; X-API-Version header present.

---

### 6) Rate‑limit Sanity (ingest)
Send ~130 requests quickly; expect some 429 responses at default RATE_LIMIT_INGEST_RPM=120:

```bash
# small burst test (idempotent no-op or small payload)
for i in $(seq 1 140); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:8080/v1/ingest \
    -H "Authorization: Bearer TEST_KEY" \
    -H "Content-Type: application/json" \
    --data '{"collector_id":"test","format":"flows.v1","records":[]}' &
done
wait
```

**Pass criteria**: mixture of 200/202 and 429 after the threshold; logs show rate‑limit hits, no crashes.

---

### 7) Metrics + Basic Auth
```bash
# If metrics behind basic auth: set BASIC_AUTH_USER/BASIC_AUTH_PASS in .env
curl -i -u "$BASIC_AUTH_USER:$BASIC_AUTH_PASS" http://localhost:8080/v1/metrics | head -n 20
```

**Pass criteria**: 200 OK and Prometheus metrics text.

---

### 8) Dead‑letter Check
If any output connector fails, payloads should land in ops/deadletter/...:

```bash
ls -R ops/deadletter || true
```

**Pass criteria**: Empty when connectors are healthy; otherwise files present with timestamps.

---

### 9) Optional: Splunk HEC & Elastic Tests
Only if you have test endpoints/tokens ready.

#### Splunk HEC config:
```bash
./scripts/configure_splunk.sh
# Then send a test ingest (already done) and verify HEC receives events.
```

#### Elastic config:
```bash
./scripts/configure_elastic.sh
# Verify index exists and documents arrive (Kibana/ES cat indices).
```

---

### 10) Clean Up
```bash
docker compose down
```

**Done. If all pass, Stage 3 is validated locally.**

---

## 📁 Postman Collection (Optional)

If you prefer Postman, import this minimal collection (save as `Telemetry-API.postman_collection.json` and import):

```json
{
  "info": { 
    "name": "Telemetry API v0.3.0", 
    "_postman_id": "d2e7c6d4-6d3a-4a2a-9e7a-telemetry", 
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json" 
  },
  "item": [
    {
      "name": "Health",
      "request": {
        "method": "GET",
        "header": [{ "key": "Authorization", "value": "Bearer TEST_KEY" }],
        "url": { "raw": "http://localhost:8080/v1/health", "host": ["http://localhost:8080"], "path": ["v1","health"] }
      }
    },
    {
      "name": "Version",
      "request": {
        "method": "GET",
        "header": [{ "key": "Authorization", "value": "Bearer TEST_KEY" }],
        "url": { "raw": "http://localhost:8080/v1/version", "host": ["http://localhost:8080"], "path": ["v1","version"] }
      }
    },
    {
      "name": "Schema",
      "request": {
        "method": "GET",
        "header": [{ "key": "Authorization", "value": "Bearer TEST_KEY" }],
        "url": { "raw": "http://localhost:8080/v1/schema", "host": ["http://localhost:8080"], "path": ["v1","schema"] }
      }
    },
    {
      "name": "Lookup",
      "request": {
        "method": "POST",
        "header": [
          { "key": "Authorization", "value": "Bearer TEST_KEY" },
          { "key": "Content-Type", "value": "application/json" }
        ],
        "body": { "mode": "raw", "raw": "{\n  \"ip\": \"8.8.8.8\"\n}" },
        "url": { "raw": "http://localhost:8080/v1/lookup", "host": ["http://localhost:8080"], "path": ["v1","lookup"] }
      }
    },
    {
      "name": "Ingest (flows.v1)",
      "request": {
        "method": "POST",
        "header": [
          { "key": "Authorization", "value": "Bearer TEST_KEY" },
          { "key": "Content-Type", "value": "application/json" }
        ],
        "body": { "mode": "raw", "raw": "{\n  \"collector_id\": \"test\",\n  \"format\": \"flows.v1\",\n  \"records\": [\n    {\n      \"ts\": 1723351200.456,\n      \"src_ip\": \"10.0.1.10\",\n      \"src_port\": 51544,\n      \"dst_ip\": \"93.184.216.34\",\n      \"dst_port\": 443,\n      \"protocol\": \"tcp\",\n      \"bytes\": 12345,\n      \"packets\": 18\n    }\n  ]\n}" },
        "url": { "raw": "http://localhost:8080/v1/ingest", "host": ["http://localhost:8080"], "path": ["v1","ingest"] }
      }
    },
    {
      "name": "Metrics (basic auth)",
      "request": {
        "method": "GET",
        "auth": { "type": "basic", "basic": [{ "key": "username", "value": "{{METRICS_USER}}" }, { "key": "password", "value": "{{METRICS_PASS}}" }] },
        "url": { "raw": "http://localhost:8080/v1/metrics", "host": ["http://localhost:8080"], "path": ["v1","metrics"] }
      }
    }
  ],
  "variable": [
    { "key": "METRICS_USER", "value": "metrics" },
    { "key": "METRICS_PASS", "value": "changeme" }
  ]
}
```

### Using Postman:
1. Set `Authorization: Bearer TEST_KEY` header for all non‑metrics calls
2. Import the collection, run Health → Version → Schema → Lookup → Ingest
3. For Metrics, set the basic auth variables to match your .env values

---

## ❓ FAQ

**Postman vs Cursor?**
- Either works. Cursor executes the exact shell flow (great for repeatable automation)
- Postman is handy for quick visual checks and sharing with others

**Where do enriched fields appear?**
- In the ingest responses/logs (and downstream outputs)
- Use `./scripts/logs.sh` or check your ES/Splunk test endpoints

**How do I raise ingest RPM to 600?**
- Set `RATE_LIMIT_INGEST_RPM=600` in .env (or export env) and `docker compose up -d` again

**What if tests fail?**
- Check container logs: `./scripts/logs.sh`
- Verify environment: `docker compose ps`
- Restart services: `docker compose restart`

---

## ✅ Success Criteria

If all steps pass, Stage 3 contract alignment is validated locally:

- ✅ All endpoints respond correctly
- ✅ Rate limiting works as expected
- ✅ Schema validation passes
- ✅ Sample data ingests successfully
- ✅ Metrics and health checks work
- ✅ No errors in container logs

**Ready for production deployment!** 🚀
