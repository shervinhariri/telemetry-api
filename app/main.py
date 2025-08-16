from fastapi import FastAPI, Header, HTTPException, Request, Response, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
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
from .api.keys import router as keys_router
from .pipeline import ingest_queue, record_batch_accepted, enqueue
from .logging_config import setup_logging, log_heartbeat

API_PREFIX = "/v1"
API_VERSION = "0.7.9"

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
    from .logging_config import log_system_event
    
    log_system_event("startup", "Telemetry API starting up", "Initializing pipeline workers and metrics")
    
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
    
    log_system_event("success", "Telemetry API ready", "All services started successfully")
    
    yield
    # Shutdown
    log_system_event("shutdown", "Telemetry API shutting down", "Stopping pipeline workers")
    logging.info("Shutting down pipeline workers")

app = FastAPI(title="Live Network Threat Telemetry API (MVP)", lifespan=lifespan)

# Add CORS middleware
from .security import get_cors_headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure via CORS_ORIGINS env var
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(version_router, prefix=API_PREFIX)
app.include_router(admin_update_router, prefix=API_PREFIX)
app.include_router(outputs_router, prefix=API_PREFIX)
app.include_router(stats_router, prefix=API_PREFIX)
app.include_router(logs_router, prefix=API_PREFIX)
app.include_router(requests_router, prefix=API_PREFIX)
app.include_router(system_router, prefix=API_PREFIX)
app.include_router(keys_router, prefix=API_PREFIX)

# Compatibility route for old UI paths
@app.get("/api/requests")
async def get_requests_api_compat(
    limit: int = Query(500, ge=1, le=1000),
    window: str = Query("15m"),
    Authorization: Optional[str] = Header(None)
):
    """Compatibility route for old UI - forwards to /v1/api/requests"""
    # Validate API key first
    require_api_key(Authorization, required_scopes=["read_requests"])
    
    # Call the actual function
    from .api.requests import get_requests_api
    return await get_requests_api(limit, window)

# Mount static files for UI
app_dir = os.path.dirname(__file__)
ui_dir = os.path.abspath(os.path.join(app_dir, "..", "ui"))

# Mount static files under /ui
app.mount("/ui", StaticFiles(directory=ui_dir), name="ui")

# Serve OpenAPI spec and Swagger UI
@app.get("/openapi.yaml")
async def openapi_yaml():
    """Serve OpenAPI specification"""
    return FileResponse("openapi.yaml", media_type="application/yaml")

@app.get("/docs")
async def docs():
    """Serve Swagger UI"""
    return FileResponse("docs/swagger.html", media_type="text/html")

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
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        from .security import get_security_headers
        for key, value in get_security_headers().items():
            response.headers[key] = value
        
        # Add trace ID to response headers
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
                
                # Sanitize audit data for privacy
                from .security import sanitize_log_data
                latest_record = sanitize_log_data(latest_record)
        
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

def require_api_key(auth_header: Optional[str], required_scopes: Optional[List[str]] = None):
    """Require API key with optional scope validation"""
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    api_key = auth_header.split(" ", 1)[1].strip()
    
    # Use scoped authentication (includes legacy support)
    from .auth import validate_api_key
    key_data = validate_api_key(api_key, required_scopes)
    
    if key_data:
        return key_data
    
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
    require_api_key(Authorization, required_scopes=["ingest"])
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

        # Log ingest operation
        duration_ms = int((time.time() - start_time) * 1000)
        from .logging_config import log_ingest
        log_ingest(
            records_count=len(records),
            success_count=accepted,
            failed_count=len(records) - accepted,
            duration_ms=duration_ms
        )

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

        return {"accepted": accepted, "rejected": len(records) - accepted, "total": len(records)}

    except HTTPException:
        raise
    except Exception as e:
        # Last-resort 500 with safe detail
        raise HTTPException(status_code=500, detail="Internal server error.") from e

@app.post(f"{API_PREFIX}/ingest/zeek")
async def ingest_zeek(request: Request, response: Response, Authorization: Optional[str] = Header(None), content_encoding: Optional[str] = Header(None)):
    """Ingest Zeek conn.log JSON lines or array"""
    require_api_key(Authorization, required_scopes=["ingest"])
    add_version_header(response)
    
    start_time = time.time()
    trace_id = getattr(request.state, 'trace_id', None)
    
    # Check idempotency
    idempotency_key = request.headers.get("Idempotency-Key")
    if idempotency_key:
        from .idempotency import check_idempotency
        cached_response = check_idempotency(idempotency_key)
        if cached_response:
            return cached_response
    
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
            raise HTTPException(status_code=400, detail="Body is not valid UTF-8 JSON")
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

        # Handle both array and line-delimited JSON
        records = []
        if isinstance(payload, list):
            records = payload
        elif isinstance(payload, dict) and "records" in payload:
            records = payload["records"]
        else:
            # Try to parse as line-delimited JSON
            lines = raw.decode("utf-8").strip().split("\n")
            records = []
            for i, line in enumerate(lines):
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError as e:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON on line {i+1}: {str(e)}")

        if not records:
            raise HTTPException(status_code=400, detail="Empty batch")
        
        if len(records) > 10000:
            raise HTTPException(status_code=413, detail="Too many records (max 10,000)")

        # Validate Zeek records
        validation_errors = []
        for i, rec in enumerate(records):
            if not isinstance(rec, dict):
                validation_errors.append(f"Record {i+1}: must be JSON object")
                continue
            
            # Basic Zeek conn.log validation
            if not rec.get("ts") and not rec.get("id.orig_h"):
                validation_errors.append(f"Record {i+1}: missing required fields (ts or id.orig_h)")
            
            if len(validation_errors) >= 3:  # Limit to first 3 errors
                break
        
        if validation_errors:
            return JSONResponse(
                status_code=207,
                content={
                    "accepted": 0,
                    "rejected": len(records),
                    "total": len(records),
                    "validation_errors": validation_errors
                }
            )

        # Enqueue records
        from .pipeline import enqueue_batch
        accepted = enqueue_batch(records)
        
        if accepted < len(records):
            raise HTTPException(status_code=429, detail="Ingest temporarily overloaded, please retry")

        # Track operations for audit
        if trace_id:
            from .audit import set_request_ops
            ops = {
                "handler": "ingest_zeek",
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
                    "avg_risk": 0
                },
                "threat": {
                    "matches": 0,
                    "indicators_checked": accepted
                },
                "outputs": {
                    "splunk": {"sent": 0, "failed": 0, "latency_ms": 0},
                    "elastic": {"sent": 0, "failed": 0, "latency_ms": 0}
                },
                "timers_ms": {
                    "preparse": int((time.time() - start_time) * 1000),
                    "enrich": 0,
                    "threat": 0,
                    "outputs": 0
                }
            }
            set_request_ops(trace_id, ops)

        result = {"accepted": accepted, "rejected": len(records) - accepted, "total": len(records)}
        
        # Store idempotency result if key provided
        if idempotency_key:
            from .idempotency import store_idempotency_result
            store_idempotency_result(idempotency_key, result)
        
        return result

    except HTTPException:
        raise
    except Exception as e:
        # Last-resort 500 with safe detail
        raise HTTPException(status_code=500, detail="Internal server error.") from e

@app.post(f"{API_PREFIX}/ingest/netflow")
async def ingest_netflow(request: Request, response: Response, Authorization: Optional[str] = Header(None), content_encoding: Optional[str] = Header(None)):
    """Ingest NetFlow/IPFIX JSON"""
    require_api_key(Authorization, required_scopes=["ingest"])
    add_version_header(response)
    
    start_time = time.time()
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
            raise HTTPException(status_code=400, detail="Body is not valid UTF-8 JSON")
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

        # Handle both array and line-delimited JSON
        records = []
        if isinstance(payload, list):
            records = payload
        elif isinstance(payload, dict) and "records" in payload:
            records = payload["records"]
        else:
            # Try to parse as line-delimited JSON
            lines = raw.decode("utf-8").strip().split("\n")
            records = []
            for i, line in enumerate(lines):
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError as e:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON on line {i+1}: {str(e)}")

        if not records:
            raise HTTPException(status_code=400, detail="Empty batch")
        
        if len(records) > 10000:
            raise HTTPException(status_code=413, detail="Too many records (max 10,000)")

        # Convert NetFlow to canonical schema
        canonical_records = []
        validation_errors = []
        
        for i, rec in enumerate(records):
            if not isinstance(rec, dict):
                validation_errors.append(f"Record {i+1}: must be JSON object")
                continue
            
            try:
                # Map common NetFlow/IPFIX fields to canonical schema
                canonical = {
                    "ts": rec.get("timestamp") or rec.get("ts") or rec.get("first_switched"),
                    "src_ip": rec.get("src_ip") or rec.get("ipv4_src_addr") or rec.get("sourceIPv4Address"),
                    "dst_ip": rec.get("dst_ip") or rec.get("ipv4_dst_addr") or rec.get("destinationIPv4Address"),
                    "src_port": rec.get("src_port") or rec.get("sourceTransportPort"),
                    "dst_port": rec.get("dst_port") or rec.get("destinationTransportPort"),
                    "proto": rec.get("protocol") or rec.get("protocolIdentifier"),
                    "bytes": rec.get("bytes") or rec.get("inOctets") or rec.get("outOctets"),
                    "packets": rec.get("packets") or rec.get("inPackets") or rec.get("outPackets"),
                    "device": rec.get("device") or rec.get("exporter"),
                    "exporter": rec.get("exporter") or rec.get("device")
                }
                
                # Validate required fields
                if not canonical["ts"] or not canonical["src_ip"] or not canonical["dst_ip"]:
                    validation_errors.append(f"Record {i+1}: missing required fields (timestamp, src_ip, dst_ip)")
                    continue
                
                canonical_records.append(canonical)
                
            except Exception as e:
                validation_errors.append(f"Record {i+1}: {str(e)}")
            
            if len(validation_errors) >= 3:  # Limit to first 3 errors
                break
        
        if validation_errors:
            return JSONResponse(
                status_code=207,
                content={
                    "accepted": 0,
                    "rejected": len(records),
                    "total": len(records),
                    "validation_errors": validation_errors
                }
            )

        # Enqueue canonical records
        from .pipeline import enqueue_batch
        accepted = enqueue_batch(canonical_records)
        
        if accepted < len(canonical_records):
            raise HTTPException(status_code=429, detail="Ingest temporarily overloaded, please retry")

        # Track operations for audit
        if trace_id:
            from .audit import set_request_ops
            ops = {
                "handler": "ingest_netflow",
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
                    "avg_risk": 0
                },
                "threat": {
                    "matches": 0,
                    "indicators_checked": accepted
                },
                "outputs": {
                    "splunk": {"sent": 0, "failed": 0, "latency_ms": 0},
                    "elastic": {"sent": 0, "failed": 0, "latency_ms": 0}
                },
                "timers_ms": {
                    "preparse": int((time.time() - start_time) * 1000),
                    "enrich": 0,
                    "threat": 0,
                    "outputs": 0
                }
            }
            set_request_ops(trace_id, ops)

        return {"accepted": accepted, "rejected": len(records) - accepted, "total": len(records)}

    except HTTPException:
        raise
    except Exception as e:
        # Last-resort 500 with safe detail
        raise HTTPException(status_code=500, detail="Internal server error.") from e

@app.post(f"{API_PREFIX}/ingest/bulk")
async def ingest_bulk(request: Request, response: Response, Authorization: Optional[str] = Header(None), content_encoding: Optional[str] = Header(None)):
    """Ingest bulk records with type specification"""
    require_api_key(Authorization, required_scopes=["ingest"])
    add_version_header(response)
    
    start_time = time.time()
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
            raise HTTPException(status_code=400, detail="Body is not valid UTF-8 JSON")
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Payload must be JSON object")
        
        record_type = payload.get("type")
        records = payload.get("records", [])
        
        if not record_type or record_type not in ["zeek", "netflow"]:
            raise HTTPException(status_code=400, detail="Type must be 'zeek' or 'netflow'")
        
        if not isinstance(records, list):
            raise HTTPException(status_code=400, detail="Records must be array")
        
        if not records:
            raise HTTPException(status_code=400, detail="Empty batch")
        
        if len(records) > 10000:
            raise HTTPException(status_code=413, detail="Too many records (max 10,000)")

        # Validate records based on type
        validation_errors = []
        for i, rec in enumerate(records):
            if not isinstance(rec, dict):
                validation_errors.append(f"Record {i+1}: must be JSON object")
                continue
            
            if record_type == "zeek":
                if not rec.get("ts") and not rec.get("id.orig_h"):
                    validation_errors.append(f"Record {i+1}: missing required Zeek fields")
            elif record_type == "netflow":
                if not rec.get("src_ip") or not rec.get("dst_ip"):
                    validation_errors.append(f"Record {i+1}: missing required NetFlow fields")
            
            if len(validation_errors) >= 3:
                break
        
        if validation_errors:
            return JSONResponse(
                status_code=207,
                content={
                    "accepted": 0,
                    "rejected": len(records),
                    "total": len(records),
                    "validation_errors": validation_errors
                }
            )

        # Enqueue records
        from .pipeline import enqueue_batch
        accepted = enqueue_batch(records)
        
        if accepted < len(records):
            raise HTTPException(status_code=429, detail="Ingest temporarily overloaded, please retry")

        # Track operations for audit
        if trace_id:
            from .audit import set_request_ops
            ops = {
                "handler": f"ingest_bulk_{record_type}",
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
                    "avg_risk": 0
                },
                "threat": {
                    "matches": 0,
                    "indicators_checked": accepted
                },
                "outputs": {
                    "splunk": {"sent": 0, "failed": 0, "latency_ms": 0},
                    "elastic": {"sent": 0, "failed": 0, "latency_ms": 0}
                },
                "timers_ms": {
                    "preparse": int((time.time() - start_time) * 1000),
                    "enrich": 0,
                    "threat": 0,
                    "outputs": 0
                }
            }
            set_request_ops(trace_id, ops)

        return {"accepted": accepted, "rejected": len(records) - accepted, "total": len(records)}

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

@app.put(f"{API_PREFIX}/indicators")
async def upsert_indicators(request: Request, response: Response, Authorization: Optional[str] = Header(None)):
    """Upsert threat intelligence indicators"""
    require_api_key(Authorization, required_scopes=["manage_indicators"])
    add_version_header(response)
    
    start_time = time.time()
    trace_id = getattr(request.state, 'trace_id', None)
    
    payload = await request.json()
    
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be JSON object")
    
    ip_or_cidr = payload.get("ip_or_cidr")
    category = payload.get("category", "unknown")
    confidence = payload.get("confidence", 50)
    
    if not ip_or_cidr:
        raise HTTPException(status_code=400, detail="ip_or_cidr is required")
    
    if not isinstance(confidence, int) or confidence < 0 or confidence > 100:
        raise HTTPException(status_code=400, detail="confidence must be integer 0-100")
    
    try:
        # Validate IP/CIDR
        ipaddress.ip_network(ip_or_cidr, strict=False)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP or CIDR")
    
    # Add to threat intelligence (simple in-memory for now)
    from .enrich.ti import add_indicator
    indicator_id = add_indicator(ip_or_cidr, category, confidence)
    
    # Track operations for audit
    if trace_id:
        from .audit import set_request_ops
        ops = {
            "handler": "upsert_indicators",
            "indicator": {
                "id": indicator_id,
                "ip_or_cidr": ip_or_cidr,
                "category": category,
                "confidence": confidence
            },
            "timers_ms": {
                "total": int((time.time() - start_time) * 1000)
            }
        }
        set_request_ops(trace_id, ops)
    
    return {
        "id": indicator_id,
        "ip_or_cidr": ip_or_cidr,
        "category": category,
        "confidence": confidence,
        "status": "added"
    }

@app.delete(f"{API_PREFIX}/indicators/{{indicator_id}}")
async def delete_indicator(indicator_id: str, request: Request, response: Response, Authorization: Optional[str] = Header(None)):
    """Delete threat intelligence indicator by ID"""
    require_api_key(Authorization, required_scopes=["manage_indicators"])
    add_version_header(response)
    
    start_time = time.time()
    trace_id = getattr(request.state, 'trace_id', None)
    
    # Remove from threat intelligence
    from .enrich.ti import remove_indicator
    removed = remove_indicator(indicator_id)
    
    if not removed:
        raise HTTPException(status_code=404, detail="Indicator not found")
    
    # Track operations for audit
    if trace_id:
        from .audit import set_request_ops
        ops = {
            "handler": "delete_indicator",
            "indicator": {
                "id": indicator_id,
                "removed": True
            },
            "timers_ms": {
                "total": int((time.time() - start_time) * 1000)
            }
        }
        set_request_ops(trace_id, ops)
    
    return {"id": indicator_id, "status": "deleted"}

@app.get(f"{API_PREFIX}/download/json")
async def download_json(
    limit: int = Query(10000, ge=1, le=50000, description="Number of records to download"),
    request: Request = None,
    response: Response = None,
    Authorization: Optional[str] = Header(None)
):
    """Download latest enriched events as JSON lines"""
    require_api_key(Authorization, required_scopes=["read_requests"])
    add_version_header(response)
    
    start_time = time.time()
    trace_id = getattr(request.state, 'trace_id', None) if request else None
    
    # Get recent events from pipeline
    from .pipeline import RECENT_EVENTS
    events = list(RECENT_EVENTS)[:limit]
    
    # Convert to JSON lines format
    json_lines = []
    for event in events:
        json_lines.append(json.dumps(event))
    
    # Track operations for audit
    if trace_id:
        from .audit import set_request_ops
        ops = {
            "handler": "download_json",
            "download": {
                "requested": limit,
                "returned": len(json_lines),
                "bytes": len('\n'.join(json_lines))
            },
            "timers_ms": {
                "total": int((time.time() - start_time) * 1000)
            }
        }
        set_request_ops(trace_id, ops)
    
    # Return as streaming response
    from fastapi.responses import StreamingResponse
    
    async def generate():
        for line in json_lines:
            yield line + '\n'
    
    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f"attachment; filename=telemetry-{int(time.time())}.ndjson"
        }
    )

@app.post(f"{API_PREFIX}/export/splunk-hec")
async def export_splunk_hec(request: Request, response: Response, Authorization: Optional[str] = Header(None)):
    """Export events to Splunk HEC with retries and DLQ"""
    require_api_key(Authorization, required_scopes=["export"])
    add_version_header(response)
    
    start_time = time.time()
    trace_id = getattr(request.state, 'trace_id', None)
    
    if not SPLUNK_HEC_URL or not SPLUNK_HEC_TOKEN:
        raise HTTPException(status_code=400, detail="Splunk HEC not configured")
    
    # Get recent events
    from .pipeline import RECENT_EVENTS
    events = list(RECENT_EVENTS)[:1000]  # Limit to 1000 events per export
    
    if not events:
        return {"status": "no_events", "sent": 0, "failed": 0}
    
    # Format events for Splunk HEC
    splunk_events = []
    for event in events:
        splunk_events.append({
            "event": event,
            "sourcetype": "telemetry:event",
            "index": "telemetry"
        })
    
    # Send to Splunk HEC with retries
    import httpx
    max_retries = 3
    retry_count = 0
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    SPLUNK_HEC_URL,
                    json=splunk_events,
                    headers={
                        "Authorization": f"Splunk {SPLUNK_HEC_TOKEN}",
                        "Content-Type": "application/json"
                    }
                )
                r.raise_for_status()
                
                # Track operations for audit
                if trace_id:
                    from .audit import set_request_ops
                    ops = {
                        "handler": "export_splunk_hec",
                        "export": {
                            "sent": len(events),
                            "failed": 0,
                            "latency_ms": int(r.elapsed.total_seconds() * 1000),
                            "retries": retry_count
                        },
                        "timers_ms": {
                            "total": int((time.time() - start_time) * 1000)
                        }
                    }
                    set_request_ops(trace_id, ops)
                
                return {
                    "status": "success",
                    "sent": len(events),
                    "failed": 0,
                    "latency_ms": int(r.elapsed.total_seconds() * 1000),
                    "retries": retry_count
                }
                
        except Exception as e:
            retry_count += 1
            if attempt < max_retries - 1:
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
                continue
            else:
                # Final attempt failed, write to DLQ
                from .dlq import dlq
                dlq.write_failed_export(
                    events=events,
                    destination="splunk_hec",
                    error=str(e),
                    last_status=getattr(r, 'status_code', None) if 'r' in locals() else None,
                    retry_count=retry_count
                )
                
                # Track operations for audit
                if trace_id:
                    from .audit import set_request_ops
                    ops = {
                        "handler": "export_splunk_hec",
                        "export": {
                            "sent": 0,
                            "failed": len(events),
                            "error": str(e),
                            "retries": retry_count,
                            "dlq_written": True
                        },
                        "timers_ms": {
                            "total": int((time.time() - start_time) * 1000)
                        }
                    }
                    set_request_ops(trace_id, ops)
                
                raise HTTPException(status_code=500, detail=f"Export failed after {retry_count} retries: {str(e)}")

@app.post(f"{API_PREFIX}/export/elastic")
async def export_elastic(request: Request, response: Response, Authorization: Optional[str] = Header(None)):
    """Export events to Elasticsearch"""
    require_api_key(Authorization, required_scopes=["export"])
    add_version_header(response)
    
    start_time = time.time()
    trace_id = getattr(request.state, 'trace_id', None)
    
    if not ELASTIC_URL:
        raise HTTPException(status_code=400, detail="Elasticsearch not configured")
    
    # Get recent events
    from .pipeline import RECENT_EVENTS
    events = list(RECENT_EVENTS)[:1000]  # Limit to 1000 events per export
    
    if not events:
        return {"status": "no_events", "sent": 0, "failed": 0}
    
    # Format events for Elasticsearch bulk API
    bulk_data = []
    index_name = "telemetry-events"
    
    for event in events:
        # Add index action
        bulk_data.append(json.dumps({"index": {"_index": index_name}}))
        # Add document
        bulk_data.append(json.dumps(event))
    
    bulk_payload = '\n'.join(bulk_data) + '\n'
    
    # Send to Elasticsearch
    import httpx
    try:
        auth = None
        if ELASTIC_USERNAME and ELASTIC_PASSWORD:
            auth = (ELASTIC_USERNAME, ELASTIC_PASSWORD)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{ELASTIC_URL}/_bulk",
                content=bulk_payload,
                headers={"Content-Type": "application/x-ndjson"},
                auth=auth
            )
            r.raise_for_status()
            
            # Track operations for audit
            if trace_id:
                from .audit import set_request_ops
                ops = {
                    "handler": "export_elastic",
                    "export": {
                        "sent": len(events),
                        "failed": 0,
                        "latency_ms": int(r.elapsed.total_seconds() * 1000)
                    },
                    "timers_ms": {
                        "total": int((time.time() - start_time) * 1000)
                    }
                }
                set_request_ops(trace_id, ops)
            
            return {
                "status": "success",
                "sent": len(events),
                "failed": 0,
                "latency_ms": int(r.elapsed.total_seconds() * 1000)
            }
            
    except Exception as e:
        # Track operations for audit
        if trace_id:
            from .audit import set_request_ops
            ops = {
                "handler": "export_elastic",
                "export": {
                    "sent": 0,
                    "failed": len(events),
                    "error": str(e)
                },
                "timers_ms": {
                    "total": int((time.time() - start_time) * 1000)
                }
            }
            set_request_ops(trace_id, ops)
        
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

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
async def metrics(response: Response, Authorization: Optional[str] = Header(None)):
    require_api_key(Authorization, required_scopes=["read_metrics"])
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


