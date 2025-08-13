🚀 **Tomorrow Morning Task: Stage 4 Pro Dashboard Validation (v1.4.0)**

**Goal**: Run the production bundle locally (Docker), validate endpoints against the Stage 1–2 contract, and ingest real sample logs generated on the fly.

**Repo**: `shervinhariri/telemetry-api`  
**Tag**: `v0.3.0`

---

**📋 Execute commands exactly as provided, in order. If a step fails, fix and re‑run.**

---

**0) Prep Workspace**
```bash
git fetch --all --tags
git checkout v0.3.0
cp -n .env.example .env
sed -i.bak 's/^API_KEY=.*/API_KEY=TEST_KEY/' .env || gsed -i 's/^API_KEY=.*/API_KEY=TEST_KEY/' .env
export RATE_LIMIT_INGEST_RPM=${RATE_LIMIT_INGEST_RPM:-120}
export RATE_LIMIT_DEFAULT_RPM=${RATE_LIMIT_DEFAULT_RPM:-600}
```

**1) Build & Launch Services**
```bash
docker compose pull || true
docker compose build --pull
docker compose up -d
docker compose ps
./scripts/test_health.sh
```
*Pass criteria: GET /v1/health returns 200 and response includes X-API-Version.*

**2) Run Test Suite**
```bash
./scripts/run_tests.sh
```
*Pass criteria: All unit/integration tests pass; schema validation completes with no errors.*

**3) Generate Sample Logs**
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

**4) Ingest Tests**
```bash
# Test flows
curl -i -X POST http://localhost:8080/v1/ingest \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data @samples/generated/flows_sample.json

# Test zeek.conn
curl -i -X POST http://localhost:8080/v1/ingest \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data @samples/generated/zeek_conn_sample.json

# Check logs
./scripts/logs.sh | tail -n +1
```

**5) Contract Endpoints Check**
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

**6) Rate-limit Test**
```bash
for i in $(seq 1 140); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:8080/v1/ingest \
    -H "Authorization: Bearer TEST_KEY" \
    -H "Content-Type: application/json" \
    --data '{"collector_id":"test","format":"flows.v1","records":[]}' &
done
wait
```
*Pass criteria: mixture of 200/202 and 429 after threshold.*

**7) Metrics Check**
```bash
curl -i -u "$BASIC_AUTH_USER:$BASIC_AUTH_PASS" http://localhost:8080/v1/metrics | head -n 20
```

**8) Dead-letter Check**
```bash
ls -R ops/deadletter || true
```

**9) Clean Up**
```bash
docker compose down
```

---

**✅ Success Criteria**: All endpoints respond correctly, rate limiting works, schema validation passes, sample data ingests successfully, metrics and health checks work, no errors in container logs.

**Ready for production deployment!** 🚀

---

**📁 Optional Postman Collection**: See `TOMORROW_TASK.md` for complete Postman collection and detailed instructions.

**❓ FAQ**:
- **Postman vs Cursor?** Either works. Cursor for automation, Postman for visual checks
- **Enriched fields?** In ingest responses/logs and downstream outputs
- **Raise RPM to 600?** Set `RATE_LIMIT_INGEST_RPM=600` in .env and restart
- **Tests fail?** Check logs: `./scripts/logs.sh`, verify: `docker compose ps`

