# Live Network Threat Telemetry API — MVP (Stage 3)

[![Docker CI](https://github.com/shervinhariri/telemetry-api/actions/workflows/docker.yml/badge.svg)](https://github.com/shervinhariri/telemetry-api/actions/workflows/docker.yml)

Local-first MVP to ingest **Zeek `conn.log` JSON**, enrich with GeoIP/ASN + threatlist, and return enriched JSON.

## Quickstart (local)

1) Put MaxMind DBs + a sample threat CSV in `./data/`:
```
data/GeoLite2-City.mmdb
data/GeoLite2-ASN.mmdb
data/threats.csv
```

2) Build and run:
```bash
docker build -t telemetry-api:0.1.0 .
docker run -d -p 8080:8080 \
  -e API_KEY=TEST_KEY \
  -e GEOIP_DB_CITY=/data/GeoLite2-City.mmdb \
  -e GEOIP_DB_ASN=/data/GeoLite2-ASN.mmdb \
  -e THREATLIST_CSV=/data/threats.csv \
  -v $PWD/data:/data:ro \
  --name tel-api telemetry-api:0.1.0
```

3) Test:
```bash
curl -s http://localhost:8080/v1/health | jq .
curl -s -X POST http://localhost:8080/v1/ingest \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data @samples/zeek_conn.json | jq .
```

## Env vars

- `API_KEY` – bearer token required for /v1/* endpoints
- `GEOIP_DB_CITY`, `GEOIP_DB_ASN` – paths to MaxMind mmdbs
- `THREATLIST_CSV` – path to a simple CSV with columns: `ip_or_cidr,category,confidence`

## Limits (from Step 2 – applied later)
- Format: `zeek.conn.v1` only in Stage 3
- Batch size/limits & rate limiting to be added in Stage 4
