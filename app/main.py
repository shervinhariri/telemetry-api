from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, List, Dict, Any
import os
import ipaddress
import json
import uuid
from datetime import datetime
from pathlib import Path
from .enrich.geoip import GeoIPEnricher
from .enrich.asn import ASNEnricher
from .enrich.threat import ThreatMatcher
from .enrich.score import RiskScorer

API_PREFIX = "/v1"
API_VERSION = "1.0.0"

API_KEY = os.getenv("API_KEY", "TEST_KEY")
GEOIP_DB_CITY = os.getenv("GEOIP_DB_CITY", "/data/GeoLite2-City.mmdb")
GEOIP_DB_ASN = os.getenv("GEOIP_DB_ASN", "/data/GeoLite2-ASN.mmdb")
THREATLIST_CSV = os.getenv("THREATLIST_CSV", "/data/threats.csv")

# Output configurations
SPLUNK_HEC_URL = os.getenv("SPLUNK_HEC_URL")
SPLUNK_HEC_TOKEN = os.getenv("SPLUNK_HEC_TOKEN")
ELASTIC_URL = os.getenv("ELASTIC_URL")
ELASTIC_USERNAME = os.getenv("ELASTIC_USERNAME")
ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD")

app = FastAPI(title="Live Network Threat Telemetry API (MVP)")

# Mount static files for UI
app_dir = os.path.dirname(__file__)
ui_dir = os.path.abspath(os.path.join(app_dir, "..", "ui"))

# Mount static files under /ui
app.mount("/ui", StaticFiles(directory=ui_dir), name="ui")

# Serve index.html at root
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(os.path.join(ui_dir, "index.html"))

# Enrichers are loaded once on startup
geo = GeoIPEnricher(GEOIP_DB_CITY)
asn = ASNEnricher(GEOIP_DB_ASN)
threats = ThreatMatcher(THREATLIST_CSV)
scorer = RiskScorer()

# Create deadletter directory
DEADLETTER_DIR = Path("ops/deadletter")
DEADLETTER_DIR.mkdir(parents=True, exist_ok=True)

def require_api_key(auth_header: Optional[str]):
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth_header.split(" ", 1)[1].strip()
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

def add_version_header(response: Response):
    response.headers["X-API-Version"] = API_VERSION

def write_deadletter(payload: Dict[str, Any], reason: str):
    """Write failed payloads to deadletter queue"""
    timestamp = datetime.now().strftime("%Y%m%d/%H%M%S")
    filename = f"{timestamp}-{uuid.uuid4()}.jsonl"
    filepath = DEADLETTER_DIR / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w') as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "payload": payload
        }) + "\n")

@app.get(f"{API_PREFIX}/health")
async def health(response: Response):
    add_version_header(response)
    return {"status": "ok"}

@app.get(f"{API_PREFIX}/version")
async def version(response: Response):
    add_version_header(response)
    return {
        "version": API_VERSION,
        "git_tag": os.getenv("GIT_TAG", "unknown"),
        "image_digest": os.getenv("IMAGE_DIGEST", "unknown")
    }

@app.get(f"{API_PREFIX}/schema")
async def schema(response: Response):
    add_version_header(response)
    return {
        "enriched_schema": "enriched.v1.schema.json",
        "input_schemas": {
            "zeek.conn.v1": "zeek.conn.v1.schema.json",
            "flows.v1": "flows.v1.schema.json"
        }
    }

@app.post(f"{API_PREFIX}/ingest")
async def ingest(request: Request, response: Response, Authorization: Optional[str] = Header(None)):
    require_api_key(Authorization)
    add_version_header(response)
    
    # Check content length (5MB limit)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large (max 5MB)")
    
    payload = await request.json()
    
    # Validate format
    fmt = payload.get("format")
    if fmt not in ["zeek.conn.v1", "flows.v1"]:
        raise HTTPException(status_code=400, detail="Unsupported format")
    
    records = payload.get("records", [])
    if len(records) > 10000:
        raise HTTPException(status_code=413, detail="Too many records (max 10,000)")
    
    # Enrich records
    enr_records = []
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
        if src_ip:
            enr["src_geo"] = geo.lookup(src_ip)
            enr["src_asn"] = asn.lookup(src_ip)
        if dst_ip:
            enr["dst_geo"] = geo.lookup(dst_ip)
            enr["dst_asn"] = asn.lookup(dst_ip)
        
        # Threat matching
        matches = threats.match_any([ip for ip in [src_ip, dst_ip] if ip])
        enr["threat"] = {"matches": matches, "matched": len(matches) > 0}
        
        # Risk scoring
        score, reasons = scorer.score(enr)
        enr["risk_score"] = score
        enr["reasons"] = reasons
        
        enr_records.append(enr)
    
    # Try to send to outputs
    try:
        if SPLUNK_HEC_URL and SPLUNK_HEC_TOKEN:
            # TODO: Implement Splunk HEC sending
            pass
    except Exception as e:
        write_deadletter(payload, f"splunk_failure: {str(e)}")
    
    try:
        if ELASTIC_URL and ELASTIC_USERNAME and ELASTIC_PASSWORD:
            # TODO: Implement Elasticsearch sending
            pass
    except Exception as e:
        write_deadletter(payload, f"elastic_failure: {str(e)}")
    
    return {
        "collector_id": payload.get("collector_id"),
        "format": fmt,
        "count": len(enr_records),
        "records": enr_records
    }

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
    
    return {
        "ip": ip,
        "geo": geo.lookup(ip),
        "asn": asn.lookup(ip),
        "threats": threats.match_any([ip])
    }

@app.post(f"{API_PREFIX}/outputs/splunk")
async def configure_splunk(request: Request, response: Response, Authorization: Optional[str] = Header(None)):
    require_api_key(Authorization)
    add_version_header(response)
    
    payload = await request.json()
    global SPLUNK_HEC_URL, SPLUNK_HEC_TOKEN
    
    SPLUNK_HEC_URL = payload.get("hec_url")
    SPLUNK_HEC_TOKEN = payload.get("token")
    
    return {"status": "configured", "hec_url": SPLUNK_HEC_URL}

@app.post(f"{API_PREFIX}/outputs/elastic")
async def configure_elastic(request: Request, response: Response, Authorization: Optional[str] = Header(None)):
    require_api_key(Authorization)
    add_version_header(response)
    
    payload = await request.json()
    global ELASTIC_URL, ELASTIC_USERNAME, ELASTIC_PASSWORD
    
    ELASTIC_URL = payload.get("url")
    ELASTIC_USERNAME = payload.get("username")
    ELASTIC_PASSWORD = payload.get("password")
    
    return {"status": "configured", "url": ELASTIC_URL}

@app.post(f"{API_PREFIX}/alerts/rules")
async def configure_alerts(request: Request, response: Response, Authorization: Optional[str] = Header(None)):
    require_api_key(Authorization)
    add_version_header(response)
    
    # TODO: Implement alert rules configuration
    return {"status": "not_implemented"}

@app.get(f"{API_PREFIX}/metrics")
async def metrics(response: Response):
    add_version_header(response)
    # TODO: Implement Prometheus metrics
    return {
        "requests_total": 0,
        "requests_failed": 0,
        "records_processed": 0
    }

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(os.path.join(ui_dir, "index.html"))
