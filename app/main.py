from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
import os
import ipaddress
import json
import uuid
import gzip
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from .enrich.geoip import GeoIPEnricher
from .enrich.asn import ASNEnricher
from .enrich.threat import ThreatMatcher
from .enrich.score import RiskScorer
from .api.version import router as version_router
from .api.admin_update import router as admin_update_router
from .api.outputs import router as outputs_router
from .api.stats import router as stats_router
from .api.logs import router as logs_router
from .pipeline import ingest_queue, record_batch_accepted, enqueue
from .logging_config import setup_logging, log_heartbeat

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

# Configure logging with rotating file handler
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from .pipeline import worker_loop
    # Start two worker processes
    asyncio.create_task(worker_loop())
    asyncio.create_task(worker_loop())
    logging.info("Stage 6 pipeline workers started (2x)")
    yield
    # Shutdown
    logging.info("Shutting down pipeline workers")

app = FastAPI(title="Live Network Threat Telemetry API (MVP)", lifespan=lifespan)

# Include API routers
app.include_router(version_router, prefix=API_PREFIX)
app.include_router(admin_update_router, prefix=API_PREFIX)
app.include_router(outputs_router, prefix=API_PREFIX)
app.include_router(stats_router, prefix=API_PREFIX)
app.include_router(logs_router, prefix=API_PREFIX)

# Mount static files for UI
app_dir = os.path.dirname(__file__)
ui_dir = os.path.abspath(os.path.join(app_dir, "..", "ui"))

# Mount static files under /ui
app.mount("/ui", StaticFiles(directory=ui_dir), name="ui")

# Serve index.html at root
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(os.path.join(ui_dir, "index.html"))

# ---------- Stage 5 Helper Functions ----------
def _maybe_gunzip(body: bytes, content_encoding: Optional[str]) -> bytes:
    if (content_encoding or "").lower() == "gzip":
        return gzip.decompress(body)
    # also auto-detect gz magic number (1F 8B) to be forgiving
    if len(body) >= 2 and body[0] == 0x1F and body[1] == 0x8B:
        return gzip.decompress(body)
    return body

def _parse_records(obj: Any) -> List[Dict[str, Any]]:
    # Accept raw array OR {"records": [...]}
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict) and "records" in obj and isinstance(obj["records"], list):
        return obj["records"]
    raise HTTPException(status_code=400, detail="Expected JSON array or object with 'records' array.")

def _validate_record(rec: Dict[str, Any]) -> None:
    # Minimal validation per contract: require timestamps + src/dst basics (expand as needed)
    required_any = ["ts", "time", "@timestamp"]
    if not any(k in rec for k in required_any):
        raise HTTPException(status_code=400, detail="Missing event timestamp.")
    # You can add per-schema checks (flows.v1, zeek.conn.v1) later

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
    return {"status": "ok", "service": "telemetry-api", "version": "v1"}

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
async def ingest(request: Request, response: Response, Authorization: Optional[str] = Header(None), content_encoding: Optional[str] = Header(None)):
    require_api_key(Authorization)
    add_version_header(response)
    
    try:
        # Check content length (5MB limit)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Payload too large (max 5MB)")
        
        raw = await request.body()
        raw = _maybe_gunzip(raw, content_encoding)
        
        try:
            payload = json.loads(raw.decode("utf-8"))
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Body is not valid UTF-8 JSON (use gzip or utf-8).")
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

        records = _parse_records(payload)
        if not records:
            raise HTTPException(status_code=400, detail="Empty batch.")
        
        if len(records) > 10000:
            raise HTTPException(status_code=413, detail="Too many records (max 10,000)")

        # Validate & enqueue
        accepted = 0
        for rec in records:
            if not isinstance(rec, dict):
                raise HTTPException(status_code=400, detail="Records must be JSON objects.")
            _validate_record(rec)
            try:
                enqueue(rec)
                accepted += 1
            except Exception:
                raise HTTPException(status_code=429, detail="Ingest temporarily overloaded, please retry.")

        record_batch_accepted(len(records))
        return {"status": "accepted", "queued": accepted}

    except HTTPException:
        raise
    except Exception as e:
        # Last-resort 500 with safe detail
        raise HTTPException(status_code=500, detail="Internal server error.") from e

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
    from .pipeline import get_stats
    stats = get_stats()
    return {
        "requests_total": 0,
        "requests_failed": 0,
        "records_processed": stats["records_processed"],
        "queue_depth": stats["queue_depth"],
        "records_queued": 0,  # TODO: increment this counter
        "eps": stats["eps"]
    }

# ---------- Stage 6 Pipeline Functions ----------
def write_deadletter(record: Dict[str, Any], reason: str):
    """Write failed record to dead letter queue"""
    try:
        dlq_file = Path("/data/deadletter.ndjson")
        with open(dlq_file, "a") as f:
            f.write(json.dumps({
                "record": record,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }) + "\n")
    except Exception as e:
        logging.error(f"Failed to write to dead letter queue: {e}")


