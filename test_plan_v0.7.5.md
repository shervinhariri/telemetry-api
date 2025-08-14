# Telemetry API v0.7.5 – GUI & API Test Plan
**Date:** 2025-08-14  
**Build:** v0.7.5  
**Scope:** Validate fresh deployment end‑to‑end: API endpoints, enrichment pipeline, audit logs, and GUI tabs.

---

## 1) Quick Smoke (CLI)
```bash
# Health
curl -sS http://localhost:80/v1/health

# Version
curl -sS http://localhost:80/v1/version

# Single lookup
curl -sS -X POST http://localhost:80/v1/lookup \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data '{"ip":"8.8.8.8"}' | jq .
```

**Expected:**
- 200 OK from /health with status=ok, uptime increasing
- Version shows 0.7.5
- /lookup returns enriched JSON with geo, asn, risk, and threat_matches

## 2) Ingest → Enrichment → Metrics
```bash
# Batch ingest (1 record)
curl -sS -X POST http://localhost:80/v1/ingest \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data @ingest_sample.json | jq .
```

**Expected:**
- Response: { "status": "accepted", "queued": 1 }
- /metrics increases: records_processed, requests_total
- GUI Dashboard shows non‑zero Events Ingested, Threat Matches, Avg Risk

## 3) GUI Acceptance – Minimalist Pass/Fail

### Dashboard
- ✅ Cards update within 5s auto‑refresh
- ✅ Threat Matches count increases after ingest
- ✅ Avg Risk shows value 0–100
- ✅ Sparklines animate with new points

### Requests
- ✅ Summary shows request counters (>= prior values)
- ✅ List shows latest POST /ingest and POST /lookup entries
- ✅ Status 200, latency, and body size visible

### System
- ✅ Uptime increasing; CPU, RSS, and queue lag visible
- ✅ Content wraps correctly (no overflow out of page)
- ✅ Version badge: shows v0.7.5

### Logs
- ✅ Live tail shows new lines while generating traffic
- ✅ "Download last 2MB" produces a file and content is readable
- ✅ Filters by level (INFO/WARN/ERROR) work

## 4) Output Connectors (optional if configured)
```bash
# Splunk HEC check (example)
curl -sS -X POST http://localhost:80/v1/outputs/splunk \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data '{"hec_url":"https://splunk.example.com:8088/services/collector","token":"***","sourcetype":"telemetry"}'

# Elastic check (example)
curl -sS -X POST http://localhost:80/v1/outputs/elastic \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data '{"bulk_url":"https://elastic.example.com/_bulk","index":"telemetry-*"}'
```

**Expected:** 200 response with configured: true or status object.

## 5) Negative/Load Tests
- ✅ 401 when Authorization missing/invalid
- ✅ 413 when batch > 5MB gz
- ✅ 429 when > 600 req/min (rate limiter)
- ✅ Ingest burst: 10×50 rec; GUI keeps up

## 6) Troubleshooting Hints
- If GUI shows flat lines: check /metrics JSON, confirm ingest responses accepted > 0
- If no enrichment: verify GeoIP/ASN DB mounted and TI lists loaded on startup
- If Logs tab empty: ensure log level ≥ INFO and websocket tail connected
- If System tab overflows: test at 1200px width; ensure CSS wraps
