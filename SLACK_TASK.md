🚀 **Tomorrow Morning Task: Stage 4 Pro Dashboard Validation (v1.4.0)**

**Goal**: Implement end-to-end enrichment and live metrics to make the dashboard come alive. Add GeoIP/ASN/Threat Intel enrichment, real-time metrics with sliding windows, and proper UI wiring for moving tiles and sparklines.

**Repo**: `shervinhariri/telemetry-api`  
**Tag**: `v1.4.0`

---

**📋 Execute commands exactly as provided, in order. If a step fails, fix and re‑run.**

---

**0) Prep Workspace & Data**
```bash
git fetch --all --tags
git checkout stage4-pro-dashboard

# Create data directories
mkdir -p geo ti data

# Create sample threat indicators
cat > ti/indicators.txt <<'EOF'
45.149.3.0/24
94.26.0.0/16
domain:evil-example.com
domain:cnc.badco.org
EOF

# Update environment
cp -n .env.example .env
sed -i.bak 's/^API_KEY=.*/API_KEY=TEST_KEY/' .env || gsed -i 's/^API_KEY=.*/API_KEY=TEST_KEY/' .env

# Add enrichment environment variables
cat >> .env <<'EOF'

# Enrichment Configuration
GEOIP_CITY_DB=/data/geo/GeoLite2-City.mmdb
GEOIP_ASN_DB=/data/geo/GeoLite2-ASN.mmdb
TI_PATH=/data/ti/indicators.txt
ENRICH_ENABLE_GEOIP=true
ENRICH_ENABLE_ASN=true
ENRICH_ENABLE_TI=true
EXPORT_ELASTIC_ENABLED=false
EXPORT_SPLUNK_ENABLED=false
EOF
```

**1) Implement Enrichment Modules**
```bash
# Create enrichment modules (see TOMORROW_TASK.md for full code)
mkdir -p app/enrich
# Create: app/enrich/geo.py, app/enrich/ti.py, app/enrich/risk.py
# Create: app/metrics.py with live aggregator
```

**2) Update API with Enrichment**
```bash
# Update app/main.py to integrate enrichment and metrics
# Wire enrichment into ingest endpoint
# Update metrics endpoint with live data
```

**3) Build & Test**
```bash
docker compose build --pull
docker compose up -d
./scripts/test_health.sh
```
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

**4) Load Test with Enrichment**
```bash
# Create load test script
cat > test_enrichment.py <<'PY'
import json, time, random, requests
import ipaddress

def rand_ip():
    if random.random() < 0.1:
        return f"45.149.3.{random.randint(1,254)}"
    return str(ipaddress.IPv4Address(random.randint(0,2**32-1)))

def event():
    return {
        "src_ip": rand_ip(),
        "dst_ip": "8.8.8.8",
        "src_port": random.randint(1024,65535),
        "dst_port": random.choice([53,80,443,445,3389,1433,22,23]),
        "bytes": random.randint(200, 5_000_000),
        "protocol": random.choice(["tcp","udp"]),
        "ts": int(time.time()*1000)
    }

print("Starting enrichment load test...")
buf = []
for i in range(2000):
    buf.append(event())
    if len(buf) == 100:
        try:
            response = requests.post(
                "http://localhost:8080/v1/ingest",
                headers={"Authorization": "Bearer TEST_KEY"},
                json={"collector_id": "test-enrich", "format": "flows.v1", "records": buf}
            )
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
        except Exception as e:
            print(f"Request failed: {e}")
        buf = []
        time.sleep(0.1)
print("Load test complete!")
PY

python3 test_enrichment.py
```

**5) Validate Live Metrics**
```bash
# Check metrics are live
curl -s http://localhost:8080/v1/metrics | jq

# Test enrichment lookup
curl -s -X POST http://localhost:8080/v1/lookup \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data '{"ip":"8.8.8.8"}' | jq
```

**6) UI Validation**
```bash
# If dashboard UI is running, verify:
# - Events Ingested tile shows live rates
# - Threat Matches increases with 45.149.3.x hits
# - Avg Risk reflects scoring
# - Sparklines move every 5 seconds
# - Queue Lag shows realistic values
```

**7) Clean Up**
```bash
docker compose down
```

---

**✅ Success Criteria**: Real enrichment working (GeoIP, ASN, TI, risk scoring), live metrics with sliding windows, moving tiles and sparklines, threat detection working (45.149.3.x hits), risk scoring reflects rules, queue lag tracking, time series data for charts.

**Dashboard is now alive and responsive!** 🚀

---

**📁 Full Implementation**: See `TOMORROW_TASK.md` for complete enrichment modules, metrics system, and detailed implementation.

**❓ FAQ**:
- **Why are tiles moving now?** Real enrichment adds processing time, live metrics track rates over time, threat detection creates variable load
- **How to adjust risk scoring?** Edit `app/enrich/risk.py` scoring rules and restart API
- **Where do enriched fields appear?** In `/v1/ingest` responses, `/v1/lookup` results, and downstream exports
- **How to add more threat indicators?** Edit `ti/indicators.txt` and restart API
- **Performance impact?** GeoIP lookups add ~1-2ms per record, TI matching is fast, risk scoring is negligible

