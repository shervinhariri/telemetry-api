# 🚀 Tomorrow Morning Task: Stage 4 Pro Dashboard Validation (v1.4.0)

## Goal
Implement end-to-end enrichment and live metrics to make the dashboard come alive. Add GeoIP/ASN/Threat Intel enrichment, real-time metrics with sliding windows, and proper UI wiring for moving tiles and sparklines.

## Repository & Tag
- **Repo**: `shervinhariri/telemetry-api`
- **Tag**: `v1.4.0`
- **Branch**: `stage4-pro-dashboard`

## 📋 Implementation Steps

**Execute commands exactly as provided, in order. If a step fails, fix and re‑run.**

---

### 0) Prep Workspace & Data
```bash
git fetch --all --tags
git checkout stage4-pro-dashboard

# Create data directories
mkdir -p geo ti data

# Download sample MaxMind databases (or use your own)
# Place GeoLite2-City.mmdb and GeoLite2-ASN.mmdb in ./geo/

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

---

### 1) Implement Enrichment Modules

#### A) Create GeoIP/ASN Enrichment
```bash
mkdir -p app/enrich
```

Create `app/enrich/geo.py`:
```python
import os
import ipaddress
from typing import Dict, Optional

try:
    import geoip2.database
    GEOIP_AVAILABLE = True
except ImportError:
    GEOIP_AVAILABLE = False

class GeoIPEnricher:
    def __init__(self):
        self.city_db = None
        self.asn_db = None
        self.enable_geoip = os.getenv("ENRICH_ENABLE_GEOIP", "true").lower() == "true"
        self.enable_asn = os.getenv("ENRICH_ENABLE_ASN", "true").lower() == "true"
        
        if self.enable_geoip and GEOIP_AVAILABLE:
            city_db_path = os.getenv("GEOIP_CITY_DB")
            if city_db_path and os.path.exists(city_db_path):
                try:
                    self.city_db = geoip2.database.Reader(city_db_path)
                except Exception:
                    pass
        
        if self.enable_asn and GEOIP_AVAILABLE:
            asn_db_path = os.getenv("GEOIP_ASN_DB")
            if asn_db_path and os.path.exists(asn_db_path):
                try:
                    self.asn_db = geoip2.database.Reader(asn_db_path)
                except Exception:
                    pass
    
    def enrich_geo_asn(self, ip: str) -> Optional[Dict]:
        if not ip:
            return None
            
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return None
            
        result = {"geo": None, "asn": None}
        
        # GeoIP lookup
        if self.city_db:
            try:
                response = self.city_db.city(ip)
                result["geo"] = {
                    "country": response.country.iso_code,
                    "city": response.city.name,
                    "lat": response.location.latitude,
                    "lon": response.location.longitude
                }
            except Exception:
                pass
        
        # ASN lookup
        if self.asn_db:
            try:
                response = self.asn_db.asn(ip)
                result["asn"] = {
                    "asn": response.autonomous_system_number,
                    "org": response.autonomous_system_organization
                }
            except Exception:
                pass
        
        return result

# Global instance
geo_enricher = GeoIPEnricher()
enrich_geo_asn = geo_enricher.enrich_geo_asn
```

#### B) Create Threat Intelligence Module
Create `app/enrich/ti.py`:
```python
import os
import ipaddress
from typing import List, Set
from pathlib import Path

class ThreatIntel:
    def __init__(self):
        self.ip_ranges: Set[ipaddress.IPv4Network] = set()
        self.domains: Set[str] = set()
        self.load_indicators()
    
    def load_indicators(self):
        ti_path = os.getenv("TI_PATH")
        if not ti_path or not os.path.exists(ti_path):
            return
            
        try:
            with open(ti_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    if line.startswith('domain:'):
                        self.domains.add(line[8:])
                    else:
                        try:
                            self.ip_ranges.add(ipaddress.IPv4Network(line))
                        except ValueError:
                            continue
        except Exception:
            pass
    
    def match_ip(self, ip: str) -> List[str]:
        if not ip:
            return []
            
        try:
            ip_obj = ipaddress.IPv4Address(ip)
        except ValueError:
            return []
            
        matches = []
        for network in self.ip_ranges:
            if ip_obj in network:
                matches.append(str(network))
        return matches
    
    def match_domain(self, domain: str) -> List[str]:
        if not domain:
            return []
        return [d for d in self.domains if domain == d]

# Global instance
threat_intel = ThreatIntel()
match_ip = threat_intel.match_ip
match_domain = threat_intel.match_domain
```

#### C) Create Risk Scoring Module
Create `app/enrich/risk.py`:
```python
from typing import Dict, List

def score(event: Dict, ti_matches: List[str]) -> int:
    """
    Deterministic v1 risk scoring:
    - Base: 10
    - +60 if TI match
    - +10 if dst_port in {23,445,1433,3389} or (bytes > 1_000_000 and src_port >= 1024)
    - Clamp 0..100
    """
    score = 10  # Base score
    
    # Threat intelligence matches
    if ti_matches:
        score += 60
    
    # Risky ports
    dst_port = event.get('dst_port') or event.get('id_resp_p')
    if dst_port in [23, 445, 1433, 3389]:
        score += 10
    
    # High bandwidth from ephemeral ports
    src_port = event.get('src_port') or event.get('id_orig_p')
    bytes_transferred = event.get('bytes') or event.get('orig_bytes', 0)
    if src_port and src_port >= 1024 and bytes_transferred > 1_000_000:
        score += 10
    
    return max(0, min(100, score))
```

---

### 2) Implement Live Metrics System

Create `app/metrics.py`:
```python
import time
import threading
from collections import deque, defaultdict
from typing import Dict, List, Any
import statistics

class MetricsAggregator:
    def __init__(self):
        self.lock = threading.Lock()
        
        # Counters (since start)
        self.totals = {
            "events": 0,
            "batches": 0,
            "threat_matches": 0,
            "risk_sum": 0,
            "risk_count": 0
        }
        
        # Request counters
        self.requests_total = 0
        self.requests_failed = 0
        
        # Unique sources tracking
        self.unique_sources = set()
        
        # Time series windows (5 minutes at 1-second resolution)
        self.window_size = 300
        self.eps_window = deque(maxlen=self.window_size)
        self.bpm_window = deque(maxlen=self.window_size)
        self.threats_window = deque(maxlen=self.window_size)
        self.risk_window = deque(maxlen=self.window_size)
        
        # Queue lag tracking
        self.lag_samples = []
        
        # Per-second accumulators
        self.current_second = int(time.time())
        self.second_events = 0
        self.second_batches = 0
        self.second_threats = 0
        self.second_risks = []
        
        # Start background ticker
        self.running = True
        self.ticker_thread = threading.Thread(target=self._ticker, daemon=True)
        self.ticker_thread.start()
    
    def _ticker(self):
        """Background task to roll windows every second"""
        while self.running:
            time.sleep(1)
            self._roll_window()
    
    def _roll_window(self):
        with self.lock:
            now = int(time.time())
            if now > self.current_second:
                # Roll the window
                self.eps_window.append(self.second_events)
                self.bpm_window.append(self.second_batches)
                self.threats_window.append(self.second_threats)
                
                # Average risk for this second
                avg_risk = statistics.mean(self.second_risks) if self.second_risks else 0
                self.risk_window.append(avg_risk)
                
                # Reset accumulators
                self.current_second = now
                self.second_events = 0
                self.second_batches = 0
                self.second_threats = 0
                self.second_risks = []
    
    def record_request(self, success: bool = True):
        with self.lock:
            self.requests_total += 1
            if not success:
                self.requests_failed += 1
    
    def record_batch(self, events: List[Dict], threat_matches: int, lag_ms: int = 0):
        with self.lock:
            # Update totals
            self.totals["events"] += len(events)
            self.totals["batches"] += 1
            self.totals["threat_matches"] += threat_matches
            
            # Update unique sources
            for event in events:
                src_ip = event.get('src_ip') or event.get('id_orig_h')
                if src_ip:
                    self.unique_sources.add(src_ip)
            
            # Update risk totals
            for event in events:
                risk_score = event.get('risk_score', 0)
                self.totals["risk_sum"] += risk_score
                self.totals["risk_count"] += 1
                self.second_risks.append(risk_score)
            
            # Update current second
            self.second_events += len(events)
            self.second_batches += 1
            self.second_threats += threat_matches
            
            # Record lag
            if lag_ms > 0:
                self.lag_samples.append(lag_ms)
                if len(self.lag_samples) > 1000:  # Keep only recent samples
                    self.lag_samples = self.lag_samples[-1000:]
    
    def get_metrics(self) -> Dict[str, Any]:
        with self.lock:
            # Calculate rates (1-minute averages)
            eps_1m = statistics.mean(list(self.eps_window)[-60:]) if len(self.eps_window) >= 60 else 0
            bpm_1m = statistics.mean(list(self.bpm_window)[-60:]) if len(self.bpm_window) >= 60 else 0
            
            # Calculate lag percentiles
            lag_p50 = statistics.quantiles(self.lag_samples, n=2)[0] if len(self.lag_samples) >= 2 else 0
            lag_p95 = statistics.quantiles(self.lag_samples, n=20)[18] if len(self.lag_samples) >= 20 else 0
            lag_p99 = statistics.quantiles(self.lag_samples, n=100)[98] if len(self.lag_samples) >= 100 else 0
            
            # Build time series arrays
            now_ms = int(time.time() * 1000)
            timeseries = {
                "last_5m": {
                    "eps": [[now_ms - (i * 1000), val] for i, val in enumerate(reversed(list(self.eps_window)))],
                    "bpm": [[now_ms - (i * 1000), val * 60] for i, val in enumerate(reversed(list(self.bpm_window)))],
                    "threats": [[now_ms - (i * 1000), val] for i, val in enumerate(reversed(list(self.threats_window)))],
                    "avg_risk": [[now_ms - (i * 1000), val] for i, val in enumerate(reversed(list(self.risk_window)))]
                }
            }
            
            return {
                "requests_total": self.requests_total,
                "requests_failed": self.requests_failed,
                "records_processed": self.totals["events"],
                "queue_depth": 0,  # TODO: implement queue depth tracking
                "records_queued": 0,
                "eps": eps_1m,
                
                "totals": {
                    "events": self.totals["events"],
                    "batches": self.totals["batches"],
                    "threat_matches": self.totals["threat_matches"],
                    "unique_sources": len(self.unique_sources),
                    "risk_sum": self.totals["risk_sum"],
                    "risk_count": self.totals["risk_count"]
                },
                "rates": {
                    "eps_1m": eps_1m,
                    "epm_1m": eps_1m * 60,
                    "bpm_1m": bpm_1m * 60
                },
                "queue": {
                    "lag_ms_p50": int(lag_p50),
                    "lag_ms_p95": int(lag_p95),
                    "lag_ms_p99": int(lag_p99)
                },
                "timeseries": timeseries
            }
    
    def shutdown(self):
        self.running = False

# Global instance
metrics = MetricsAggregator()
```

---

### 3) Update Main API with Enrichment

Update `app/main.py` to integrate enrichment:

```python
# Add imports
from .enrich.geo import enrich_geo_asn
from .enrich.ti import match_ip
from .enrich.risk import score
from .metrics import metrics
import time

# Update ingest endpoint
@app.post(f"{API_PREFIX}/ingest")
async def ingest(request: Request, response: Response, Authorization: Optional[str] = Header(None)):
    require_api_key(Authorization)
    add_version_header(response)
    
    # Record request
    start_time = time.time()
    
    try:
        # Check content length (5MB limit)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 5 * 1024 * 1024:
            metrics.record_request(success=False)
            raise HTTPException(status_code=413, detail="Payload too large (max 5MB)")
        
        payload = await request.json()
        
        # Validate format
        fmt = payload.get("format")
        if fmt not in ["zeek.conn.v1", "flows.v1"]:
            metrics.record_request(success=False)
            raise HTTPException(status_code=400, detail="Unsupported format")
        
        records = payload.get("records", [])
        if len(records) > 10000:
            metrics.record_request(success=False)
            raise HTTPException(status_code=413, detail="Too many records (max 10,000)")
        
        # Enrich records
        enr_records = []
        total_threat_matches = 0
        
        for rec in records:
            enr = rec.copy()
            
            # Extract IPs based on format
            if fmt == "zeek.conn.v1":
                src_ip = rec.get("id_orig_h")
                dst_ip = rec.get("id_resp_h")
            elif fmt == "flows.v1":
                src_ip = rec.get("src_ip")
                dst_ip = rec.get("dst_ip")
            else:
                src_ip = dst_ip = None
            
            # Geo & ASN enrichment
            geo_asn = None
            if dst_ip or src_ip:
                geo_asn = enrich_geo_asn(dst_ip or src_ip)
                if geo_asn:
                    enr["geo"] = geo_asn.get("geo")
                    enr["asn"] = geo_asn.get("asn")
            
            # Threat matching
            ti_matches = []
            if src_ip:
                ti_matches.extend(match_ip(src_ip))
            if dst_ip:
                ti_matches.extend(match_ip(dst_ip))
            
            enr["ti"] = {"matches": ti_matches}
            total_threat_matches += len(ti_matches)
            
            # Risk scoring
            risk_score = score(enr, ti_matches)
            enr["risk_score"] = risk_score
            
            enr_records.append(enr)
        
        # Record metrics
        lag_ms = int((time.time() - start_time) * 1000)
        metrics.record_batch(enr_records, total_threat_matches, lag_ms)
        metrics.record_request(success=True)
        
        return {
            "collector_id": payload.get("collector_id"),
            "format": fmt,
            "count": len(enr_records),
            "records": enr_records
        }
        
    except Exception as e:
        metrics.record_request(success=False)
        raise

# Update metrics endpoint
@app.get(f"{API_PREFIX}/metrics")
async def get_metrics(response: Response):
    add_version_header(response)
    return metrics.get_metrics()

# Update lookup endpoint
@app.post(f"{API_PREFIX}/lookup")
async def lookup(request: Request, response: Response, Authorization: Optional[str] = Header(None)):
    require_api_key(Authorization)
    add_version_header(response)
    
    payload = await request.json()
    ip = payload.get("ip")
    
    if not ip:
        raise HTTPException(status_code=400, detail="IP address required")
    
    try:
        ipaddress.ip_address(ip)  # Validate IP
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address")
    
    # Get enrichment
    geo_asn = enrich_geo_asn(ip)
    ti_matches = match_ip(ip)
    
    return {
        "ip": ip,
        "geo": geo_asn.get("geo") if geo_asn else None,
        "asn": geo_asn.get("asn") if geo_asn else None,
        "threats": ti_matches
    }
```

---

### 4) Update Docker Compose

Update `docker-compose.yml`:
```yaml
services:
  api:
    image: ${API_IMAGE:-telemetry-api:latest}
    env_file: .env
    expose:
      - "8080"
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://localhost:8080/v1/health || exit 1"]
      interval: 10s
      timeout: 3s
      retries: 6
      start_period: 30s
    restart: unless-stopped
    volumes:
      - ./data:/data
      - ./geo/GeoLite2-City.mmdb:/data/geo/GeoLite2-City.mmdb:ro
      - ./geo/GeoLite2-ASN.mmdb:/data/geo/GeoLite2-ASN.mmdb:ro
      - ./ti/indicators.txt:/data/ti/indicators.txt:ro
    networks:
      - telemetry_network
```

---

### 5) Build & Test

```bash
# Build with new enrichment
docker compose build --pull
docker compose up -d

# Test health
./scripts/test_health.sh

# Test enrichment
curl -s -X POST http://localhost:8080/v1/lookup \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data '{"ip":"8.8.8.8"}' | jq
```

---

### 6) Load Test with Enrichment

Create and run the load test script:

```bash
cat > test_enrichment.py <<'PY'
import json, time, random, requests
import ipaddress

def rand_ip():
    # Sprinkle some hits in 45.149.3.x
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

---

### 7) Validate Live Metrics

```bash
# Check metrics are live
curl -s http://localhost:8080/v1/metrics | jq

# Expected results:
# - rates.epm_1m > 0
# - rates.bpm_1m > 0  
# - timeseries.last_5m.* arrays non-flat
# - queue.lag_ms_p95 > 0
# - requests_total increasing
# - totals.threat_matches > 0 (from 45.149.3.x hits)
```

---

### 8) UI Validation

If you have the dashboard UI running, verify:

- **Events Ingested** tile shows live rates (not frozen)
- **Threat Matches** increases when 45.149.3.x traffic hits
- **Avg Risk** reflects scoring (TI hits + risky ports)
- **Sparklines** move every 5 seconds
- **Queue Lag** shows realistic values

---

### 9) Clean Up

```bash
docker compose down
```

---

## ✅ Success Criteria

If all steps pass, Stage 4 Pro Dashboard is validated locally:

- ✅ Real enrichment (GeoIP, ASN, TI, risk scoring)
- ✅ Live metrics with sliding windows
- ✅ Moving tiles and sparklines
- ✅ Threat detection working (45.149.3.x hits)
- ✅ Risk scoring reflects rules
- ✅ Queue lag tracking
- ✅ Time series data for charts

**Dashboard is now alive and responsive!** 🚀

---

## 📁 Optional: Output Connectors

To enable Elastic/Splunk exports:

```bash
# Configure Elastic
curl -s -X POST http://localhost:8080/v1/outputs/elastic \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data '{
    "url":"http://elastic:9200",
    "index_prefix":"telemetry-enriched",
    "username":"elastic",
    "password":"changeme",
    "batch_max":2000,
    "flush_interval_ms":1500,
    "enabled":true
  }' | jq

# Configure Splunk
curl -s -X POST http://localhost:8080/v1/outputs/splunk \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data '{
    "hec_url":"https://splunk:8088/services/collector",
    "token":"changeme",
    "enabled":true
  }' | jq
```

---

## ❓ FAQ

**Why are tiles moving now?**
- Real enrichment adds processing time
- Live metrics track rates over time
- Threat detection creates variable load

**How to adjust risk scoring?**
- Edit `app/enrich/risk.py` scoring rules
- Restart API to reload

**Where do enriched fields appear?**
- In `/v1/ingest` responses
- In `/v1/lookup` results
- In downstream exports (Elastic/Splunk)

**How to add more threat indicators?**
- Edit `ti/indicators.txt`
- Restart API to reload

**Performance impact?**
- GeoIP lookups add ~1-2ms per record
- TI matching is fast (in-memory)
- Risk scoring is negligible

