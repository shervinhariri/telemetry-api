# Fix Pack v0.3 - Enrichment and Live Metrics

## Overview

This fix pack implements real enrichment, live metrics, and time-series data to make the dashboard come alive. It replaces the stubbed enrichment with working GeoIP, ASN, threat intelligence, and risk scoring.

## What's New

### 1. Real Enrichment
- **GeoIP + ASN**: Uses MaxMind databases for geographic and ASN lookup
- **Threat Intelligence**: Plain-text indicator loading with CIDR and domain matching
- **Risk Scoring**: Deterministic v1 scoring based on TI matches, risky ports, and traffic patterns

### 2. Live Metrics
- **Totals**: Events, batches, threat matches, unique sources, risk statistics
- **Rates**: Events per minute, batches per minute with 1-minute sliding windows
- **Queue Lag**: P50, P95, P99 percentiles for processing latency
- **Time Series**: Last 5 minutes of data for sparklines and charts

### 3. Enhanced API
- **/v1/lookup**: Returns enriched data for any IP (geo, asn, ti, risk)
- **/v1/metrics**: Extended with rates, queue lag, and time-series data
- **Request Tracking**: Automatic request counting and failure tracking

## Configuration

### Environment Variables
```bash
# GeoIP databases
GEOIP_CITY_DB=/data/geo/GeoLite2-City.mmdb
GEOIP_ASN_DB=/data/geo/GeoLite2-ASN.mmdb

# Threat intelligence
TI_PATH=/data/ti/indicators.txt

# Feature flags
ENRICH_ENABLE_GEOIP=true
ENRICH_ENABLE_ASN=true
ENRICH_ENABLE_TI=true
EXPORT_ELASTIC_ENABLED=false
EXPORT_SPLUNK_ENABLED=false
```

### Threat Indicators Format
Create `/data/ti/indicators.txt`:
```
# CIDR ranges
45.149.3.0/24
94.26.0.0/16

# Domains
domain:evil-example.com
domain:cnc.badco.org
```

## Risk Scoring

### V1 Scoring Rubric
- **Base Score**: 10 points
- **Threat Intelligence Match**: +60 points
- **Risky Destination Port** (23, 445, 1433, 3389): +10 points
- **High Bytes + Ephemeral Source Port**: +10 points
- **Score Range**: 0-100 (clamped)

### Example Scores
- Normal traffic: 10 points
- TI match: 70 points
- TI + risky port: 80 points
- TI + risky port + high bytes: 90 points

## Metrics Response

The `/v1/metrics` endpoint now returns:

```json
{
  "requests_total": 1234,
  "requests_failed": 0,
  "records_processed": 9010,
  "queue_depth": 0,
  "records_queued": 0,
  "eps": 17.3,
  
  "totals": {
    "events": 9010,
    "batches": 90,
    "threat_matches": 42,
    "unique_sources": 528,
    "risk_sum": 315000,
    "risk_count": 9010
  },
  
  "rates": {
    "eps_1m": 17.3,
    "epm_1m": 1038.0,
    "bpm_1m": 52.0
  },
  
  "queue": {
    "lag_ms_p50": 12,
    "lag_ms_p95": 35,
    "lag_ms_p99": 70
  },
  
  "timeseries": {
    "last_5m": {
      "eps": [[1640995200000, 15.2], ...],
      "bpm": [[1640995200000, 45.0], ...],
      "threats": [[1640995200000, 3], ...],
      "avg_risk": [[1640995200000, 25.5], ...]
    }
  }
}
```

## Testing

### Run Unit Tests
```bash
python3 tests/test_risk_scoring.py
```

### Run Integration Tests
```bash
python3 scripts/test_fix_pack.py
```

### Manual Testing
1. Start the service:
   ```bash
   docker compose up -d --build
   ```

2. Send test data:
   ```bash
   curl -X POST http://localhost:8080/v1/ingest \
     -H "Authorization: Bearer TEST_KEY" \
     -H "Content-Type: application/json" \
     -d '{"records": [{"src_ip": "45.149.3.100", "dst_ip": "8.8.8.8", "dst_port": 445, "bytes": 1000, "ts": 1640995200000}]}'
   ```

3. Check metrics:
   ```bash
   curl http://localhost:8080/v1/metrics | jq
   ```

4. Test lookup:
   ```bash
   curl -X POST http://localhost:8080/v1/lookup \
     -H "Authorization: Bearer TEST_KEY" \
     -H "Content-Type: application/json" \
     -d '{"ip": "8.8.8.8"}' | jq
   ```

## Dashboard Integration

The UI should now read:
- **Events Ingested**: `rates.epm_1m`
- **Unique Sources**: `totals.unique_sources`
- **Batches**: `rates.bpm_1m`
- **Threat Matches**: Latest from `timeseries.last_5m.threats`
- **Avg Risk**: Latest from `timeseries.last_5m.avg_risk`
- **Queue Lag**: `queue.lag_ms_p95`

Sparklines should use the arrays in `timeseries.last_5m.*`.

## Files Modified

### New Files
- `app/enrich/geo.py` - Combined GeoIP + ASN enrichment
- `app/enrich/ti.py` - Threat intelligence matching
- `app/enrich/risk.py` - Risk scoring
- `app/metrics.py` - Thread-safe metrics aggregator
- `ti/indicators.txt` - Sample threat indicators
- `scripts/test_fix_pack.py` - Integration tests
- `tests/test_risk_scoring.py` - Unit tests

### Modified Files
- `app/main.py` - Updated to use new enrichment and metrics
- `app/pipeline.py` - Enhanced with real enrichment and batch processing
- `docker-compose.yml` - Added volume mounts and environment variables

## Next Steps

1. **UI Updates**: Update dashboard to read new metrics structure
2. **Output Connectors**: Implement Elastic/Splunk exporters
3. **Alerting**: Add alert rules based on risk scores and threat matches
4. **Performance**: Optimize enrichment for high-throughput scenarios
