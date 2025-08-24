from fastapi import FastAPI, Header, HTTPException, Request, Response, Query, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .middleware import TracingMiddleware
from contextlib import asynccontextmanager, suppress
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
from .services.prometheus_metrics import prometheus_metrics
from .api.version import router as version_router
from .api.admin_update import router as admin_update_router
from .api.outputs import router as outputs_router
from .api.stats import router as stats_router
from .api.logs import router as logs_router
from .api.requests import router as requests_router
from .api.system import router as system_router
from .api.keys import router as keys_router
from .api.demo import router as demo_router
from .api.prometheus import router as prometheus_router
from .api.sources import router as sources_router
from .api.admin_security import router as admin_security_router
from .api.admin_flags import router as admin_flags_router
from .api.utils import router as utils_router
from .api.ingest import router as ingest_router
from .api.uploads import router as uploads_router
from .api.enrichment_geoip import router as geoip_cfg_router
from .pipeline import ingest_queue, record_batch_accepted, enqueue
from .logging_config import setup_logging
from .config import API_VERSION
from .auth.deps import require_scopes
from .auth.tenant import require_tenant
from . import pipeline as pipeline_mod  # import the *module*, not the FastAPI instance
from .db_init import init_schema_and_seed

# Import configuration
from .config import (
    DEMO_MODE, DEMO_EPS, DEMO_DURATION_SEC, DEMO_VARIANTS,
    API_PREFIX, API_KEY, DATABASE_URL, GEOIP_DB_CITY, GEOIP_DB_ASN,
    THREATLIST_CSV, SPLUNK_HEC_URL, SPLUNK_HEC_TOKEN,
    ELASTIC_URL, ELASTIC_USERNAME, ELASTIC_PASSWORD,
    LOG_LEVEL, LOG_FILE, RETENTION_DAYS
)

# Configure logging at import time
setup_logging()

# Test logging configuration
logger = logging.getLogger("app")
logger.info("startup: logging configured", extra={"component":"api"})

@asynccontextmanager
async def lifespan(application: FastAPI):
    # Startup
    from .pipeline import worker_loop
    from .db import SessionLocal
    try:
        from .models.apikey import ApiKey as _ApiKey
        from .models.tenant import Tenant as _Tenant
    except Exception:
        _ApiKey = None
        _Tenant = None
    
    logger = logging.getLogger("app")
    logger.info("Telemetry API starting up", extra={
        "details": "Initializing pipeline workers and metrics",
        "component": "api"
    })
    
    # Bind async primitives to the *active* event loop
    application.state.event_queue = asyncio.Queue(maxsize=10000)

    # Ensure DB schema + seed default API keys (idempotent)
    init_schema_and_seed()

    # Back-compat: point pipeline module's queue at the new loop-bound queue
    pipeline_mod.ingest_queue = application.state.event_queue

    # Start workers and keep handles for clean shutdown
    application.state.worker_tasks = [
        asyncio.create_task(pipeline_mod.worker_loop()),
        asyncio.create_task(pipeline_mod.worker_loop()),
    ]
    
    # Start metrics ticker
    async def metrics_ticker():
        while True:
            tick()
            await asyncio.sleep(1)
    
    asyncio.create_task(metrics_ticker())
    
    # DB persistence self-check
    try:
        db = SessionLocal()
        tenants = db.query(_Tenant).count() if _Tenant else 0
        keys = db.query(_ApiKey).count() if _ApiKey else 0
        db_path = os.getenv("DATABASE_URL", "sqlite:///./telemetry.db")
        logging.getLogger("telemetry").info(
            "DB_CHECK: existing_db=%s tenants=%s keys=%s url=%s",
            (tenants + keys) > 0, tenants, keys, db_path,
        )
    except Exception:
        logging.getLogger("telemetry").exception("DB_CHECK failed")
    finally:
        try:
            db.close()
        except Exception:
            pass

    logger.info("Telemetry API ready", extra={
        "details": "All services started successfully",
        "workers": 2,
        "metrics_ticker": True,
        "component": "api"
    })
    
    try:
        yield
    finally:
        # Graceful shutdown
        for t in application.state.worker_tasks:
            t.cancel()
        for t in application.state.worker_tasks:
            with suppress(asyncio.CancelledError):
                await t
        
        logger.info("Telemetry API shutting down", extra={
            "details": "Stopping pipeline workers",
            "component": "api"
        })

app = FastAPI(title="Live Network Threat Telemetry API (MVP)", lifespan=lifespan)

# Optional auto-migrate on startup
if os.getenv("AUTO_MIGRATE", "0") in ("1", "true", "True"):
    try:
        import subprocess
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        logging.getLogger("telemetry").info("Alembic auto-migrate: upgrade head OK")
    except Exception:
        logging.getLogger("telemetry").exception("Alembic auto-migrate failed")

# Add CORS middleware
from .security import get_cors_headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure via CORS_ORIGINS env var
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add tracing middleware
app.add_middleware(TracingMiddleware)

# Add API version header middleware
from starlette.middleware.base import BaseHTTPMiddleware

class ApiVersionHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-API-Version"] = "v1"
        return response

app.add_middleware(ApiVersionHeaderMiddleware)

# ------------------------------------------------------------
# Public endpoint allowlist and middleware helpers
# ------------------------------------------------------------
log = logging.getLogger("telemetry")

# Make Prometheus path public configurable (default: true)
PUBLIC_PROMETHEUS = os.getenv("PUBLIC_PROMETHEUS", "true").lower() == "true"

BASE_PUBLIC = (
    "/",
    f"{API_PREFIX}/health",
    f"{API_PREFIX}/version",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/ui/",
    "/static/",
)

PUBLIC_ALLOWLIST = BASE_PUBLIC + ((f"{API_PREFIX}/metrics/prometheus",) if PUBLIC_PROMETHEUS else ())

def _is_public(path: str) -> bool:
    # Use exact matching for specific paths, prefix matching only for directories
    for p in PUBLIC_ALLOWLIST:
        if p == '/':  # Root path - exact match only
            if path == '/':
                return True
        elif p.endswith('/'):  # Directory prefix
            if path.startswith(p):
                return True
        else:  # Exact path
            if path == p:
                return True
    return False

# Database cold-start middleware
@app.middleware("http")
async def database_cold_start_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        # Check if it's a database-related error
        error_str = str(e).lower()
        if any(db_error in error_str for db_error in [
            "no such table", "operationalerror", "database is locked", 
            "unable to open database", "database connection"
        ]):
            return JSONResponse(
                {"status": "warming_up", "detail": "database not ready"},
                status_code=503
            )
        # Re-raise other exceptions
        raise

# Authentication middleware
@app.middleware("http")
async def tenancy_middleware(request: Request, call_next):
    path = request.url.path

    # Skip auth for public paths
    if _is_public(path):
        return await call_next(request)

    # Authenticate and set tenant_id
    try:
        from .auth.deps import authenticate
        await authenticate(request)
    except HTTPException:
        # Let FastAPI return proper 401/403
        raise
    except Exception:
        # Only unexpected errors should become 500
        log.exception("Unhandled error in middleware for %s", path)
        return JSONResponse({"detail": "internal_error"}, status_code=500)

    return await call_next(request)

# Include API routers
app.include_router(version_router, prefix=API_PREFIX)
app.include_router(admin_update_router, prefix=API_PREFIX)
app.include_router(outputs_router, prefix=API_PREFIX)
app.include_router(stats_router, prefix=API_PREFIX)
app.include_router(logs_router, prefix=API_PREFIX)
app.include_router(requests_router, prefix=API_PREFIX)
app.include_router(system_router, prefix=API_PREFIX)
app.include_router(keys_router, prefix=API_PREFIX)
app.include_router(demo_router, prefix=API_PREFIX)
app.include_router(prometheus_router, prefix=API_PREFIX)
# app.include_router(sources_router, prefix=API_PREFIX)  # Disabled until implemented
app.include_router(admin_security_router, prefix=API_PREFIX)
app.include_router(admin_flags_router, prefix=API_PREFIX)
app.include_router(utils_router, prefix=API_PREFIX)
app.include_router(ingest_router, prefix=API_PREFIX)
app.include_router(uploads_router, prefix=API_PREFIX)
app.include_router(geoip_cfg_router, prefix=API_PREFIX)

# UDP Metrics endpoint for mapper reporting
@app.post(f"{API_PREFIX}/admin/metrics/udp")
async def report_udp_metrics(request: Request):
    """Accept UDP metrics from the mapper"""
    # Check if user has admin scope
    scopes = getattr(request.state, 'scopes', [])
    if "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Admin scope required")
    
    try:
        payload = await request.json()
        udp_packets = payload.get("udp_packets_received", 0)
        records_parsed = payload.get("records_parsed", 0)
        
        # Record metrics
        from .metrics import record_udp_packets_received, record_records_parsed
        if udp_packets > 0:
            record_udp_packets_received(udp_packets)
        if records_parsed > 0:
            record_records_parsed(records_parsed)
        
        return {"status": "ok", "recorded": {"udp_packets": udp_packets, "records_parsed": records_parsed}}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid metrics payload: {str(e)}")



# Compatibility route for old UI paths
@app.get("/api/requests")
async def get_requests_api_compat(
    limit: int = Query(500, ge=1, le=1000),
    window: str = Query("15m"),
    Authorization: Optional[str] = Header(None),
    request: Request = None
):
    """Compatibility route for old UI - forwards to /v1/api/requests"""
    # Check if user has read_requests scope
    scopes = getattr(request.state, 'scopes', []) if request else []
    if "read_requests" not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'read_requests' scope")
    
    # Call the actual function
    from .api.requests import get_requests_api
    return await get_requests_api(limit, window)

# Mount static files for UI (support both container and local dev paths)
app_dir = os.path.dirname(__file__)
_ui_candidates = [
    os.path.abspath(os.path.join(app_dir, "..", "ui")),             # container path (/app/ui)
    os.path.abspath(os.path.join(app_dir, "..", "ops", "ui", "ui")) # local path (repo ops/ui/ui)
]
ui_dir = next((p for p in _ui_candidates if os.path.isdir(p)), _ui_candidates[0])

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
    raise HTTPException(status_code=400, detail="Expected JSON array or object with 'records' array. Got: " + str(type(obj)))

def _validate_record(rec: Dict[str, Any]) -> None:
    # Minimal validation per contract: require timestamps + src/dst basics (expand as needed)
    required_any = ["ts", "time", "@timestamp"]
    if not any(k in rec for k in required_any):
        # Count HTTP admission drop for missing fields
        try:
            prometheus_metrics.increment_http_dropped("missing_fields")
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="Missing event timestamp. Required one of: " + ", ".join(required_any))
    
    # Validate required fields for flows.v1 format
    if "src_ip" in rec or "dst_ip" in rec:
        # This looks like a flow record, validate required fields
        required_flow_fields = ["src_ip", "dst_ip", "src_port", "dst_port", "proto"]
        missing_fields = [field for field in required_flow_fields if field not in rec]
        if missing_fields:
            try:
                prometheus_metrics.increment_http_dropped("missing_fields")
            except Exception:
                pass
            raise HTTPException(status_code=400, detail=f"Missing required flow fields: {', '.join(missing_fields)}")
    
    # You can add per-schema checks (flows.v1, zeek.conn.v1) later

# Enrichers are loaded once on startup via the new modules
# (geo, asn, threats, and scorer are now imported and used directly)

# Create deadletter directory
DEADLETTER_DIR = Path("ops/deadletter")
DEADLETTER_DIR.mkdir(parents=True, exist_ok=True)

def require_api_key(auth_header: Optional[str], required_scopes: Optional[List[str]] = None):
    """Require API key with optional scope validation - now handled by middleware"""
    # This function is now a no-op since authentication is handled by middleware
    # The middleware will have already validated the API key and set request.state
    pass

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
    # Use the same version reading logic as the version router
    from .api.version import get_version_from_file
    return {
        "version": get_version_from_file(),
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
async def ingest(request: Request, response: Response, Authorization: Optional[str] = Header(None), content_encoding: Optional[str] = Header(None), x_source_id: Optional[str] = Header(None)):
    # Check if user has ingest scope
    scopes = getattr(request.state, 'scopes', [])
    if "ingest" not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'ingest' scope")
    add_version_header(response)
    
    start_time = time.time()
    # Get trace_id from request state (set by middleware)
    trace_id = getattr(request.state, 'trace_id', None)
    
    try:
        # Check content length (5MB limit)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 5 * 1024 * 1024:
            try:
                prometheus_metrics.increment_http_dropped("over_size")
            except Exception:
                pass
            raise HTTPException(status_code=413, detail="Payload too large (max 5MB)")
        
        # Rate limiting per key and per tenant (opt-in via cache fallback-safe)
        from .services.ratelimit import check_limit, PER_MIN
        from .services.idempotency import seen_or_store

        tenant_id = request.headers.get("X-Tenant-ID") or getattr(request.state, 'tenant_id', 'default')
        api_key_id = getattr(request.state, 'key_id', 'unknown')

        if not check_limit(tenant_id, api_key_id):
            from fastapi.responses import JSONResponse
            try:
                prometheus_metrics.increment_http_dropped("over_rate")
            except Exception:
                pass
            return JSONResponse({"error": "rate_limited", "limit_per_min": PER_MIN}, status_code=429)

        raw = await request.body()
        raw = _maybe_gunzip(raw, content_encoding)
        
        try:
            payload = json.loads(raw.decode("utf-8"))
        except UnicodeDecodeError as e:
            try:
                prometheus_metrics.increment_http_dropped("invalid_json")
            except Exception:
                pass
            logger = logging.getLogger("app")
            logger.warning(f"Invalid UTF-8 in ingest payload: {str(e)}", extra={
                "trace_id": trace_id,
                "component": "ingest"
            })
            raise HTTPException(status_code=400, detail="Body is not valid UTF-8 JSON (use gzip or utf-8).")
        except json.JSONDecodeError as e:
            try:
                prometheus_metrics.increment_http_dropped("invalid_json")
            except Exception:
                pass
            logger = logging.getLogger("app")
            logger.warning(f"Invalid JSON in ingest payload: {str(e)}", extra={
                "trace_id": trace_id,
                "component": "ingest"
            })
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

        records = _parse_records(payload)
        if not records:
            try:
                prometheus_metrics.increment_http_dropped("no_records")
            except Exception:
                pass
            raise HTTPException(status_code=400, detail="Empty batch.")
        
        if len(records) > 10000:
            try:
                prometheus_metrics.increment_http_dropped("too_many_records")
            except Exception:
                pass
            raise HTTPException(status_code=413, detail="Too many records (max 10,000)")

        # Add validated event
        if trace_id:
            from .observability.audit import push_event
            push_event(request.state.audit, "validated", 
                      {"ok": True, "schema": "flows.v1", "records": len(records)})
        
        # Validate records
        for rec in records:
            if not isinstance(rec, dict):
                raise HTTPException(status_code=400, detail="Records must be JSON objects.")
            _validate_record(rec)

        # Admitted
        try:
            prometheus_metrics.increment_http_admitted(1)
        except Exception:
            pass
        
        # Admission control - check source security rules
        from .config import (
            get_admission_http_enabled, get_admission_log_only, get_admission_fail_open, get_trust_proxy
        )
        
        if get_admission_http_enabled():
            from .security import validate_http_source_admission
            from .services.sources import SourceService
            from .metrics import record_blocked_source
            from .db import SessionLocal
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Get source_id from payload or header
            source_id = payload.get("collector_id") or payload.get("source_id") or x_source_id
            
            if source_id:
                # Look up source in database
                db = SessionLocal()
                try:
                    source = SourceService.get_source_by_id(db, source_id, tenant_id)
                    if source:
                        try:
                            # Validate admission with HTTP-specific logic
                            allowed, reason = validate_http_source_admission(
                                source=source,
                                request=request,
                                record_count=len(records)
                            )
                            
                            if not allowed:
                                # Record blocked source metrics
                                record_blocked_source(source_id, reason)
                                
                                # Handle LOG_ONLY mode
                                if get_admission_log_only():
                                    logger.warning(f"Admission blocked (LOG_ONLY): source={source_id}, reason={reason}")
                                    # Continue processing (return 200)
                                else:
                                    # Return appropriate error response
                                    error_detail = {
                                        "disabled": "Source is disabled",
                                        "ip_not_allowed": "Client IP not in allowed list",
                                        "rate_limit": "Rate limit exceeded"
                                    }.get(reason, "Admission denied")
                                    
                                    return JSONResponse(
                                        {"error": reason, "detail": error_detail},
                                        status_code=403 if reason != "rate_limit" else 429
                                    )
                                    
                        except Exception as e:
                            # Handle internal errors in admission control
                            logger.error(f"Admission control error: {e}")
                            record_blocked_source(source_id, "admission_error")
                            
                            if get_admission_fail_open():
                                logger.warning(f"Admission error, FAIL_OPEN enabled - allowing request: {e}")
                                # Continue processing (return 200)
                            else:
                                return JSONResponse(
                                    {"error": "admission_error", "detail": "Internal admission control error"},
                                    status_code=500
                                )
                finally:
                    db.close()
        
        # Resolve source ID for metrics tracking
        source_id = x_source_id
        if not source_id:
            # Auto-create default HTTP source for API key
            key = Authorization.replace("Bearer ", "") if Authorization else ""
            source_id = f"default-http-{key[:8]}"
            
            # TODO: Create default source if it doesn't exist
            # This would involve database lookup/creation
        
        # Track source metrics
        from .metrics import record_source_admitted, update_source_eps
        record_source_admitted(source_id, len(records))
        
        # Calculate and update EPS
        eps = len(records) / max((time.time() - start_time), 0.001)  # Avoid division by zero
        update_source_eps(source_id, eps)
        
        # Track source origin for type mismatch detection
        if source_id:
            from .services.sources import SourceService
            from .db import SessionLocal
            db = SessionLocal()
            try:
                SourceService.track_source_origin(db, source_id, tenant_id, "http")
            except Exception as e:
                logger.error(f"Failed to track source origin: {e}")
            finally:
                db.close()
        
        # Idempotency check: if same batch seen within TTL, return 209
        if seen_or_store(tenant_id, api_key_id, raw):
            from fastapi.responses import JSONResponse
            return JSONResponse({"status": "duplicate"}, status_code=209)

        # Enqueue records using batch processing
        from .pipeline import enqueue_batch
        accepted = enqueue_batch(records)
        
        if accepted < len(records):
            raise HTTPException(status_code=429, detail="Ingest temporarily overloaded, please retry.")
        
        # Record parsed records metric
        from .metrics import record_records_parsed
        record_records_parsed(accepted)
        
        # Add enriched event (simulated for now)
        if trace_id:
            from .observability.audit import push_event
            push_event(request.state.audit, "enriched", 
                      {"geo": accepted, "asn": accepted, "ti": 0, "risk_avg": 18.7})
        
        # Add exported event (simulated for now)
        if trace_id:
            from .observability.audit import push_event
            push_event(request.state.audit, "exported", 
                      {"splunk": "ok", "elastic": "ok", "count": accepted})

        # Log ingest operation
        duration_ms = int((time.time() - start_time) * 1000)
        from .logging_config import log_ingest_operation
        log_ingest_operation(
            records_count=len(records),
            success_count=accepted,
            failed_count=len(records) - accepted,
            duration_ms=duration_ms,
            trace_id=trace_id or "unknown"
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

        # Update source metrics for successful ingest
        try:
            from .services.sources import SourceService
            from .db import SessionLocal
            
            # Get collector_id from payload or headers
            collector_id = payload.get("collector_id") or request.headers.get("X-Collector-ID") or "unknown"
            
            # Calculate average risk score from records
            risk_scores = [rec.get("risk_score", 0) for rec in records if isinstance(rec, dict)]
            avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0
            
            # Record metrics
            SourceService.record_ingest_metrics(
                collector_id=collector_id,
                record_count=accepted,
                success=True,
                risk_score=avg_risk
            )
            
            # Update last_seen for sources using this collector
            db = SessionLocal()
            try:
                SourceService.update_source_last_seen(db, collector_id, tenant_id)
            finally:
                db.close()
                
        except Exception as e:
            # Log but don't fail the ingest
            logging.getLogger("telemetry").warning(f"Failed to update source metrics: {e}")

        return {"accepted": accepted, "rejected": len(records) - accepted, "total": len(records)}

    except HTTPException:
        raise
    except Exception as e:
        # Last-resort 500 with safe detail
        raise HTTPException(status_code=500, detail="Internal server error.") from e

@app.post(f"{API_PREFIX}/ingest/zeek")
async def ingest_zeek(request: Request, response: Response, Authorization: Optional[str] = Header(None), content_encoding: Optional[str] = Header(None)):
    """Ingest Zeek conn.log JSON lines or array"""
    # Check if user has ingest scope
    scopes = getattr(request.state, 'scopes', [])
    if "ingest" not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'ingest' scope")
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
            try:
                prometheus_metrics.increment_http_dropped("over_size")
            except Exception:
                pass
            raise HTTPException(status_code=413, detail="Payload too large (max 5MB)")
        
        raw = await request.body()
        raw = _maybe_gunzip(raw, content_encoding)
        
        try:
            payload = json.loads(raw.decode("utf-8"))
        except UnicodeDecodeError:
            try:
                prometheus_metrics.increment_http_dropped("invalid_json")
            except Exception:
                pass
            raise HTTPException(status_code=400, detail="Body is not valid UTF-8 JSON")
        except json.JSONDecodeError as e:
            try:
                prometheus_metrics.increment_http_dropped("invalid_json")
            except Exception:
                pass
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
            try:
                prometheus_metrics.increment_http_dropped("no_records")
            except Exception:
                pass
            raise HTTPException(status_code=400, detail="Empty batch")
        
        if len(records) > 10000:
            try:
                prometheus_metrics.increment_http_dropped("too_many_records")
            except Exception:
                pass
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

        # Admission control - check source security rules
        from .config import (
            get_admission_http_enabled, get_admission_log_only, get_admission_fail_open
        )
        
        if get_admission_http_enabled():
            from .security import validate_http_source_admission
            from .services.sources import SourceService
            from .metrics import record_blocked_source
            from .db import SessionLocal
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Get source_id from header
            source_id = request.headers.get("X-Source-Id")
            tenant_id = request.headers.get("X-Tenant-ID") or getattr(request.state, 'tenant_id', 'default')
            
            if source_id:
                # Look up source in database
                db = SessionLocal()
                try:
                    source = SourceService.get_source_by_id(db, source_id, tenant_id)
                    if source:
                        try:
                            # Validate admission with HTTP-specific logic
                            allowed, reason = validate_http_source_admission(
                                source=source,
                                request=request,
                                record_count=len(records)
                            )
                            
                            if not allowed:
                                # Record blocked source metrics
                                record_blocked_source(source_id, reason)
                                
                                # Handle LOG_ONLY mode
                                if get_admission_log_only():
                                    logger.warning(f"Admission blocked (LOG_ONLY): source={source_id}, reason={reason}")
                                    # Continue processing (return 200)
                                else:
                                    # Return appropriate error response
                                    error_detail = {
                                        "disabled": "Source is disabled",
                                        "ip_not_allowed": "Client IP not in allowed list",
                                        "rate_limit": "Rate limit exceeded"
                                    }.get(reason, "Admission denied")
                                    
                                    return JSONResponse(
                                        {"error": reason, "detail": error_detail},
                                        status_code=403 if reason != "rate_limit" else 429
                                    )
                                    
                        except Exception as e:
                            # Handle internal errors in admission control
                            logger.error(f"Admission control error: {e}")
                            record_blocked_source(source_id, "admission_error")
                            
                            if get_admission_fail_open():
                                logger.warning(f"Admission error, FAIL_OPEN enabled - allowing request: {e}")
                                # Continue processing (return 200)
                            else:
                                return JSONResponse(
                                    {"error": "admission_error", "detail": "Internal admission control error"},
                                    status_code=500
                                )
                finally:
                    db.close()

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

        # Track source origin for type mismatch detection
        if source_id:
            from .services.sources import SourceService
            from .db import SessionLocal
            db = SessionLocal()
            try:
                SourceService.track_source_origin(db, source_id, tenant_id, "http")
            except Exception as e:
                logger.error(f"Failed to track source origin: {e}")
            finally:
                db.close()

        result = {"accepted": accepted, "rejected": len(records) - accepted, "total": len(records)}
        
        # Store idempotency result if key provided
        if idempotency_key:
            from .idempotency import store_idempotency_result
            store_idempotency_result(idempotency_key, result)
        
        try:
            prometheus_metrics.increment_http_admitted(1)
        except Exception:
            pass
        return result

    except HTTPException:
        raise
    except Exception as e:
        # Last-resort 500 with safe detail
        raise HTTPException(status_code=500, detail="Internal server error.") from e

@app.post(f"{API_PREFIX}/ingest/netflow")
async def ingest_netflow(request: Request, response: Response, Authorization: Optional[str] = Header(None), content_encoding: Optional[str] = Header(None)):
    """Ingest NetFlow/IPFIX JSON"""
    # Check if user has ingest scope
    scopes = getattr(request.state, 'scopes', [])
    if "ingest" not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'ingest' scope")
    add_version_header(response)
    
    start_time = time.time()
    trace_id = getattr(request.state, 'trace_id', None)
    
    try:
        # Check content length (5MB limit)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 5 * 1024 * 1024:
            try:
                prometheus_metrics.increment_http_dropped("over_size")
            except Exception:
                pass
            raise HTTPException(status_code=413, detail="Payload too large (max 5MB)")
        
        raw = await request.body()
        raw = _maybe_gunzip(raw, content_encoding)
        
        try:
            payload = json.loads(raw.decode("utf-8"))
        except UnicodeDecodeError:
            try:
                prometheus_metrics.increment_http_dropped("invalid_json")
            except Exception:
                pass
            raise HTTPException(status_code=400, detail="Body is not valid UTF-8 JSON")
        except json.JSONDecodeError as e:
            try:
                prometheus_metrics.increment_http_dropped("invalid_json")
            except Exception:
                pass
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
            try:
                prometheus_metrics.increment_http_dropped("no_records")
            except Exception:
                pass
            raise HTTPException(status_code=400, detail="Empty batch")
        
        if len(records) > 10000:
            try:
                prometheus_metrics.increment_http_dropped("too_many_records")
            except Exception:
                pass
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

        # Admission control - check source security rules
        from .config import (
            get_admission_http_enabled, get_admission_log_only, get_admission_fail_open
        )
        
        if get_admission_http_enabled():
            from .security import validate_http_source_admission
            from .services.sources import SourceService
            from .metrics import record_blocked_source
            from .db import SessionLocal
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Get source_id from header
            source_id = request.headers.get("X-Source-Id")
            tenant_id = request.headers.get("X-Tenant-ID") or getattr(request.state, 'tenant_id', 'default')
            
            if source_id:
                # Look up source in database
                db = SessionLocal()
                try:
                    source = SourceService.get_source_by_id(db, source_id, tenant_id)
                    if source:
                        try:
                            # Validate admission with HTTP-specific logic
                            allowed, reason = validate_http_source_admission(
                                source=source,
                                request=request,
                                record_count=len(canonical_records)
                            )
                            
                            if not allowed:
                                # Record blocked source metrics
                                record_blocked_source(source_id, reason)
                                
                                # Handle LOG_ONLY mode
                                if get_admission_log_only():
                                    logger.warning(f"Admission blocked (LOG_ONLY): source={source_id}, reason={reason}")
                                    # Continue processing (return 200)
                                else:
                                    # Return appropriate error response
                                    error_detail = {
                                        "disabled": "Source is disabled",
                                        "ip_not_allowed": "Client IP not in allowed list",
                                        "rate_limit": "Rate limit exceeded"
                                    }.get(reason, "Admission denied")
                                    
                                    return JSONResponse(
                                        {"error": reason, "detail": error_detail},
                                        status_code=403 if reason != "rate_limit" else 429
                                    )
                                    
                        except Exception as e:
                            # Handle internal errors in admission control
                            logger.error(f"Admission control error: {e}")
                            record_blocked_source(source_id, "admission_error")
                            
                            if get_admission_fail_open():
                                logger.warning(f"Admission error, FAIL_OPEN enabled - allowing request: {e}")
                                # Continue processing (return 200)
                            else:
                                return JSONResponse(
                                    {"error": "admission_error", "detail": "Internal admission control error"},
                                    status_code=500
                                )
                finally:
                    db.close()

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

        # Track source origin for type mismatch detection
        if source_id:
            from .services.sources import SourceService
            from .db import SessionLocal
            db = SessionLocal()
            try:
                # Determine origin based on endpoint
                origin = "udp" if request.url.path.endswith("/netflow") else "http"
                SourceService.track_source_origin(db, source_id, tenant_id, origin)
            except Exception as e:
                logger.error(f"Failed to track source origin: {e}")
            finally:
                db.close()

        try:
            prometheus_metrics.increment_http_admitted(1)
            # Treat accepted canonical records as UDP-admitted for head pipeline visibility
            prometheus_metrics.increment_udp_admitted(accepted)
        except Exception:
            pass
        return {"accepted": accepted, "rejected": len(records) - accepted, "total": len(records)}

    except HTTPException:
        raise
    except Exception as e:
        # Last-resort 500 with safe detail
        raise HTTPException(status_code=500, detail="Internal server error.") from e

@app.post(f"{API_PREFIX}/ingest/bulk")
async def ingest_bulk(request: Request, response: Response, Authorization: Optional[str] = Header(None), content_encoding: Optional[str] = Header(None)):
    """Ingest bulk records with type specification"""
    # Check if user has ingest scope
    scopes = getattr(request.state, 'scopes', [])
    if "ingest" not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'ingest' scope")
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

        # Admission control - check source security rules
        from .config import (
            get_admission_http_enabled, get_admission_log_only, get_admission_fail_open
        )
        
        if get_admission_http_enabled():
            from .security import validate_http_source_admission
            from .services.sources import SourceService
            from .metrics import record_blocked_source
            from .db import SessionLocal
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Get source_id from header
            source_id = request.headers.get("X-Source-Id")
            tenant_id = request.headers.get("X-Tenant-ID") or getattr(request.state, 'tenant_id', 'default')
            
            if source_id:
                # Look up source in database
                db = SessionLocal()
                try:
                    source = SourceService.get_source_by_id(db, source_id, tenant_id)
                    if source:
                        try:
                            # Validate admission with HTTP-specific logic
                            allowed, reason = validate_http_source_admission(
                                source=source,
                                request=request,
                                record_count=len(records)
                            )
                            
                            if not allowed:
                                # Record blocked source metrics
                                record_blocked_source(source_id, reason)
                                
                                # Handle LOG_ONLY mode
                                if get_admission_log_only():
                                    logger.warning(f"Admission blocked (LOG_ONLY): source={source_id}, reason={reason}")
                                    # Continue processing (return 200)
                                else:
                                    # Return appropriate error response
                                    error_detail = {
                                        "disabled": "Source is disabled",
                                        "ip_not_allowed": "Client IP not in allowed list",
                                        "rate_limit": "Rate limit exceeded"
                                    }.get(reason, "Admission denied")
                                    
                                    return JSONResponse(
                                        {"error": reason, "detail": error_detail},
                                        status_code=403 if reason != "rate_limit" else 429
                                    )
                                    
                        except Exception as e:
                            # Handle internal errors in admission control
                            logger.error(f"Admission control error: {e}")
                            record_blocked_source(source_id, "admission_error")
                            
                            if get_admission_fail_open():
                                logger.warning(f"Admission error, FAIL_OPEN enabled - allowing request: {e}")
                                # Continue processing (return 200)
                            else:
                                return JSONResponse(
                                    {"error": "admission_error", "detail": "Internal admission control error"},
                                    status_code=500
                                )
                finally:
                    db.close()

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

        # Track source origin for type mismatch detection
        if source_id:
            from .services.sources import SourceService
            from .db import SessionLocal
            db = SessionLocal()
            try:
                SourceService.track_source_origin(db, source_id, tenant_id, "http")
            except Exception as e:
                logger.error(f"Failed to track source origin: {e}")
            finally:
                db.close()

        return {"accepted": accepted, "rejected": len(records) - accepted, "total": len(records)}

    except HTTPException:
        raise
    except Exception as e:
        # Last-resort 500 with safe detail
        raise HTTPException(status_code=500, detail="Internal server error.") from e

@app.post(f"{API_PREFIX}/lookup")
async def lookup(request: Request, response: Response, Authorization: Optional[str] = Header(None)):
    # Authentication handled by middleware
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
    # Authentication handled by middleware
    add_version_header(response)
    
    payload = await request.json()
    global SPLUNK_HEC_URL, SPLUNK_HEC_TOKEN
    
    SPLUNK_HEC_URL = payload.get("hec_url")
    SPLUNK_HEC_TOKEN = payload.get("token")
    
    return {"status": "configured", "hec_url": SPLUNK_HEC_URL}

@app.post(f"{API_PREFIX}/outputs/elastic")
async def configure_elastic(request: Request, response: Response, Authorization: Optional[str] = Header(None)):
    # Authentication handled by middleware
    add_version_header(response)
    
    payload = await request.json()
    global ELASTIC_URL, ELASTIC_USERNAME, ELASTIC_PASSWORD
    
    ELASTIC_URL = payload.get("url")

@app.put(f"{API_PREFIX}/indicators")
async def upsert_indicators(request: Request, response: Response, Authorization: Optional[str] = Header(None)):
    """Upsert threat intelligence indicators"""
    # Check if user has manage_indicators scope
    scopes = getattr(request.state, 'scopes', [])
    if "manage_indicators" not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'manage_indicators' scope")
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
    # Check if user has manage_indicators scope
    scopes = getattr(request.state, 'scopes', [])
    if "manage_indicators" not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'manage_indicators' scope")
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
    # Check if user has read_requests scope
    scopes = getattr(request.state, 'scopes', []) if request else []
    if "read_requests" not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'read_requests' scope")
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
    # Check if user has export scope
    scopes = getattr(request.state, 'scopes', [])
    if "export" not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'export' scope")
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
                
                # Update Prometheus metrics
                latency_ms = int(r.elapsed.total_seconds() * 1000)
                prometheus_metrics.increment_export_sent("splunk", len(events))
                prometheus_metrics.observe_export_latency("splunk", latency_ms)
                
                # Track operations for audit
                if trace_id:
                    from .audit import set_request_ops
                    ops = {
                        "handler": "export_splunk_hec",
                        "export": {
                            "sent": len(events),
                            "failed": 0,
                            "latency_ms": latency_ms,
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
                    "latency_ms": latency_ms,
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
                
                # Update Prometheus metrics
                prometheus_metrics.increment_export_failed("splunk", "http_error", len(events))
                dlq_stats = dlq.get_dlq_stats()
                prometheus_metrics.set_export_dlq_depth("splunk", dlq_stats["total_events"])
                
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
    # Check if user has export scope
    scopes = getattr(request.state, 'scopes', [])
    if "export" not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'export' scope")
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
            
            # Update Prometheus metrics
            latency_ms = int(r.elapsed.total_seconds() * 1000)
            prometheus_metrics.increment_export_sent("elastic", len(events))
            prometheus_metrics.observe_export_latency("elastic", latency_ms)
            
            # Track operations for audit
            if trace_id:
                from .audit import set_request_ops
                ops = {
                    "handler": "export_elastic",
                    "export": {
                        "sent": len(events),
                        "failed": 0,
                        "latency_ms": latency_ms
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
                "latency_ms": latency_ms
            }
            
    except Exception as e:
        # Update Prometheus metrics
        prometheus_metrics.increment_export_failed("elastic", "http_error", len(events))
        from .dlq import dlq
        dlq_stats = dlq.get_dlq_stats()
        prometheus_metrics.set_export_dlq_depth("elastic", dlq_stats["total_events"])
        
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
    # Authentication handled by middleware
    add_version_header(response)
    
    # TODO: Implement alert rules configuration
    return {"status": "not_implemented"}



@app.get(f"{API_PREFIX}/metrics", dependencies=[Depends(require_scopes("read_metrics", "admin")), Depends(require_tenant(optional=False))])
async def metrics(response: Response, Authorization: Optional[str] = Header(None), request: Request = None):
    add_version_header(response)
    return get_metrics()

# ---------- Stage 6 Pipeline Functions ----------
def write_deadletter(record: Dict[str, Any], reason: str):
    """Write failed record to dead letter queue"""
    try:
        base = Path("/data")
        if not os.access(base.parent, os.W_OK):
            base = Path("data")
        base.mkdir(parents=True, exist_ok=True)
        dlq_file = base / "deadletter.ndjson"
        with open(dlq_file, "a") as f:
            f.write(json.dumps({
                "record": record,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }) + "\n")
    except Exception as e:
        logging.error(f"Failed to write to dead letter queue: {e}")

# Server startup configuration
if __name__ == "__main__":
    import uvicorn
    import os
    
    # Port configuration with deprecation bridge
    port = int(os.getenv("APP_PORT", "80"))
    
    # Legacy API_PORT support with deprecation warning
    legacy_port = os.getenv("API_PORT")
    if legacy_port and not os.getenv("APP_PORT"):
        port = int(legacy_port)
        import logging
        logging.warning("API_PORT is deprecated; use APP_PORT. Using API_PORT=%s", legacy_port)
    
    # Log startup configuration
    import logging
    logging.info(f"Starting Telemetry API on port {port}")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        access_log=True
    )


