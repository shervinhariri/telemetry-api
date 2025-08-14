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
import time
from datetime import datetime
from pathlib import Path
from .enrich.geo import enrich_geo_asn
from .enrich.ti import match_ip, match_domain
from .enrich.risk import score
from .metrics import get_metrics, increment_requests, tick
from .api.version import router as version_router
from .api.admin_update import router as admin_update_router
from .api.outputs import router as outputs_router
from .api.stats import router as stats_router
from .api.logs import router as logs_router
from .api.requests import router as requests_router
from .api.system import router as system_router
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
    
    # Start metrics ticker
    async def metrics_ticker():
        while True:
            tick()
            await asyncio.sleep(1)
    
    asyncio.create_task(metrics_ticker())
    logging.info("Metrics ticker started")
    
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
app.include_router(requests_router, prefix=API_PREFIX)
app.include_router(system_router, prefix=API_PREFIX)

# Mount static files for UI
app_dir = os.path.dirname(__file__)
ui_dir = os.path.abspath(os.path.join(app_dir, "..", "ui"))

# Mount static files under /ui
app.mount("/ui", StaticFiles(directory=ui_dir), name="ui")

# Middleware to track requests and audit logging
@app.middleware("http")
async def track_requests(request: Request, call_next):
    # Skip audit for static files and health checks
    if request.url.path.startswith("/ui/") or request.url.path == "/v1/health":
        response = await call_next(request)
        increment_requests(response.status_code >= 400)
        return response
    
    # Extract API key for audit
    api_key = None
    tenant_id = "unknown"
    
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        api_key = auth_header[7:]  # Remove "Bearer " prefix
        tenant_id = f"tenant_{hash(api_key) % 1000}"  # Simple tenant ID generation
    
    # Start audit context
    from .audit import audit_request, classify_result, in_memory_audit_logs, get_request_ops
    async with audit_request(request, api_key or "anonymous", tenant_id) as trace_id:
        # Store trace_id in request state for handlers to access
        request.state.trace_id = trace_id
        
        # Add trace ID to response headers
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        
        # Update the most recent audit record with response info
        if in_memory_audit_logs:
            latest_record = in_memory_audit_logs[-1]
            if latest_record.get('trace_id') == trace_id:
                latest_record['status'] = response.status_code
                latest_record['result'] = classify_result(response.status_code)
                
                # Add operations data if available
                ops = get_request_ops(trace_id)
                if ops:
                    latest_record['ops'] = ops
                
                # Add error info for 5xx responses
                if response.status_code >= 500:
                    latest_record['error'] = "Internal server error"
        
        logging.info(f"AUDIT_COMPLETE: {request.method} {request.url.path} - {response.status_code} - {trace_id}")
        
        increment_requests(response.status_code >= 400)
        return response

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

# Enrichers are loaded once on startup via the new modules
# (geo, asn, threats, and scorer are now imported and used directly)

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
    
    start_time = time.time()
    # Get trace_id from request state (set by middleware)
    trace_id = getattr(request.state, 'trace_id', None)
    
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

        # Validate records
        for rec in records:
            if not isinstance(rec, dict):
                raise HTTPException(status_code=400, detail="Records must be JSON objects.")
            _validate_record(rec)
        
        # Enqueue records using batch processing
        from .pipeline import enqueue_batch
        accepted = enqueue_batch(records)
        
        if accepted < len(records):
            raise HTTPException(status_code=429, detail="Ingest temporarily overloaded, please retry.")

        # Track operations for audit
        if trace_id:
            from .audit import set_request_ops
            ops = {
                "handler": "ingest",
                "batch": {
                    "received": len(records),
                    "accepted": accepted,
                    "rejected": len(records) - accepted,
                    "bytes": len(raw)
                },
                "enrichment": {
                    "geo": accepted,
                    "asn": accepted,
                    "risk_scored": accepted,
                    "avg_risk": 18.7  # TODO: Calculate actual average
                },
                "threat": {
                    "matches": 0,  # TODO: Track actual matches
                    "indicators_checked": accepted
                },
                "outputs": {
                    "splunk": {"sent": 0, "failed": 0, "latency_ms": 0},
                    "elastic": {"sent": 0, "failed": 0, "latency_ms": 0}
                },
                "timers_ms": {
                    "preparse": int((time.time() - start_time) * 1000),
                    "enrich": 28,
                    "threat": 6,
                    "outputs": 25
                }
            }
            set_request_ops(trace_id, ops)

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
    
    start_time = time.time()
    # Get trace_id from request state (set by middleware)
    trace_id = getattr(request.state, 'trace_id', None)
    
    payload = await request.json()
    ip = payload.get("ip")
    
    if not ip:
        raise HTTPException(status_code=400, detail="IP address required")
    
    try:
        ipaddress.ip_address(ip)  # Validate IP
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address")
    
    # Enrich the IP
    geo_asn = enrich_geo_asn(ip)
    ti_matches = match_ip(ip)
    
    # Create sample event for risk scoring
    sample_event = {"dst_ip": ip}
    risk_score = score(sample_event, ti_matches)
    
    # Track operations for audit
    if trace_id:
        from .audit import set_request_ops
        ops = {
            "handler": "lookup",
            "enrichment": {
                "geo": 1 if geo_asn else 0,
                "asn": 1 if geo_asn else 0,
                "risk_scored": 1,
                "risk": risk_score
            },
            "threat": {
                "matches": len(ti_matches),
                "indicator": ti_matches[0] if ti_matches else None
            },
            "timers_ms": {
                "total": int((time.time() - start_time) * 1000)
            }
        }
        set_request_ops(trace_id, ops)
    
    return {
        "ip": ip,
        "geo": geo_asn.get("geo") if geo_asn else None,
        "asn": geo_asn.get("asn") if geo_asn else None,
        "ti": {"matches": ti_matches},
        "risk_score": risk_score
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
    return get_metrics()

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


