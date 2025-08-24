from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, AnyHttpUrl, Field, model_validator
from typing import List, Optional, Dict, Any
import time
import httpx
import asyncio
from ..auth.deps import require_scopes
from ..services.prometheus_metrics import prometheus_metrics
from ..metrics import record_export_test
from ..dlq import dlq
import json

router = APIRouter()

class SplunkConfig(BaseModel):
    hec_url: AnyHttpUrl
    token: str
    index: str = "telemetry"
    sourcetype: str = "telemetry:event"
    batch_size: int = 500
    max_retries: int = 5
    backoff_ms: int = 200
    verify_tls: bool = True
    extra_fields: Dict[str, Any] = {}

class ElasticConfig(BaseModel):
    url: Optional[str] = None
    urls: Optional[List[str]] = None
    index: Optional[str] = "telemetry"
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def choose_url(cls, values):
        if isinstance(values, dict):
            url, urls = values.get("url"), values.get("urls")
            if not url and urls:
                values["url"] = urls[0]
            if not values.get("url"):
                raise ValueError("At least one Elastic URL is required (url or urls).")
        return values

STATE: Dict[str, Any] = {
    "splunk": None,
    "elastic": None,
}

# Health status tracking
HEALTH_STATUS: Dict[str, Dict[str, Any]] = {
    "splunk": {
        "reachable": False,
        "last_success_ts": None,
        "last_http_code": None,
        "last_error": None,
        "backlog": 0,
        "dlq_depth": 0
    },
    "elastic": {
        "reachable": False,
        "last_success_ts": None,
        "last_http_code": None,
        "last_error": None,
        "backlog": 0,
        "dlq_depth": 0
    }
}

async def test_splunk_send() -> tuple[bool, Optional[int], Optional[str]]:
    """Test send to Splunk HEC"""
    if not STATE.get("splunk"):
        return False, None, "Splunk not configured"
    
    config = STATE["splunk"]
    test_event = {
        "event": {"telemetry": "ping", "ts": time.time()},
        "sourcetype": config.get("sourcetype", "telemetry:event"),
        "index": config.get("index", "telemetry")
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                str(config["hec_url"]),
                json=[test_event],
                headers={
                    "Authorization": f"Splunk {config['token']}",
                    "Content-Type": "application/json"
                }
            )
            r.raise_for_status()
            return True, r.status_code, None
    except Exception as e:
        return False, getattr(e, 'status_code', None), str(e)

async def test_elastic_send() -> tuple[bool, Optional[int], Optional[str]]:
    """Test send to Elasticsearch"""
    if not STATE.get("elastic"):
        return False, None, "Elasticsearch not configured"
    
    config = STATE["elastic"]
    test_event = {"telemetry": "ping", "ts": time.time()}
    index_name = f"{config.get('index_prefix', 'telemetry-')}test"
    
    bulk_data = [
        json.dumps({"index": {"_index": index_name}}),
        json.dumps(test_event)
    ]
    bulk_payload = '\n'.join(bulk_data) + '\n'
    
    try:
        auth = None
        if config.get("username") and config.get("password"):
            auth = (config["username"], config["password"])
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{config['urls'][0]}/_bulk",
                content=bulk_payload,
                headers={"Content-Type": "application/x-ndjson"},
                auth=auth
            )
            r.raise_for_status()
            return True, r.status_code, None
    except Exception as e:
        return False, getattr(e, 'status_code', None), str(e)

@router.post("/outputs/splunk")
@router.put("/outputs/splunk")
def set_splunk(cfg: SplunkConfig):
    STATE["splunk"] = cfg.model_dump()
    return {"status": "ok", "splunk": STATE["splunk"]}

@router.get("/outputs/splunk")
def get_splunk():
    return {
        "splunk": STATE["splunk"],
        "health": HEALTH_STATUS["splunk"]
    }

@router.post("/outputs/splunk/test")
async def test_splunk(request: Request):
    """Test Splunk HEC connectivity"""
    # Check authorization
    scopes = getattr(request.state, 'scopes', [])
    if "export" not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'export' or 'admin' scope")
    
    t0 = time.perf_counter()
    ok, code, err = await test_splunk_send()
    ms = int((time.perf_counter() - t0) * 1000)
    
    # Update metrics
    record_export_test("splunk", 1)
    prometheus_metrics.increment_export_test("splunk", str(code or 0))
    
    # Update health status
    if ok:
        HEALTH_STATUS["splunk"]["reachable"] = True
        HEALTH_STATUS["splunk"]["last_success_ts"] = time.time()
        HEALTH_STATUS["splunk"]["last_http_code"] = code
        HEALTH_STATUS["splunk"]["last_error"] = None
    else:
        HEALTH_STATUS["splunk"]["reachable"] = False
        HEALTH_STATUS["splunk"]["last_http_code"] = code
        HEALTH_STATUS["splunk"]["last_error"] = err
    
    return {
        "status": "ok" if ok else "fail",
        "latency_ms": ms,
        "http_code": code,
        "error": err
    }

@router.post("/outputs/elastic")
@router.put("/outputs/elastic")
def set_elastic(cfg: ElasticConfig):
    try:
        STATE["elastic"] = cfg.model_dump()
        return {"status": "ok"}
    except ValueError as e:
        return JSONResponse(status_code=422, content={"status": "error", "error": str(e)})

@router.get("/outputs/elastic")
def get_elastic():
    return {
        "elastic": STATE["elastic"],
        "health": HEALTH_STATUS["elastic"]
    }

@router.post("/outputs/elastic/test")
async def test_elastic(request: Request):
    """Test Elasticsearch connectivity"""
    # Check authorization
    scopes = getattr(request.state, 'scopes', [])
    if "export" not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'export' or 'admin' scope")
    
    t0 = time.perf_counter()
    ok, code, err = await test_elastic_send()
    ms = int((time.perf_counter() - t0) * 1000)
    
    # Update metrics
    record_export_test("elastic", 1)
    prometheus_metrics.increment_export_test("elastic", str(code or 0))
    
    # Update health status
    if ok:
        HEALTH_STATUS["elastic"]["reachable"] = True
        HEALTH_STATUS["elastic"]["last_success_ts"] = time.time()
        HEALTH_STATUS["elastic"]["last_http_code"] = code
        HEALTH_STATUS["elastic"]["last_error"] = None
    else:
        HEALTH_STATUS["elastic"]["reachable"] = False
        HEALTH_STATUS["elastic"]["last_http_code"] = code
        HEALTH_STATUS["elastic"]["last_error"] = err
    
    return {
        "status": "ok" if ok else "fail",
        "latency_ms": ms,
        "http_code": code,
        "error": err
    }

@router.get("/outputs/status")
def get_outputs_status():
    """Get comprehensive outputs status including health"""
    # Update DLQ depths
    try:
        dlq_stats = dlq.get_dlq_stats()
        HEALTH_STATUS["splunk"]["dlq_depth"] = dlq_stats.get("total_events", 0)
        HEALTH_STATUS["elastic"]["dlq_depth"] = dlq_stats.get("total_events", 0)
    except:
        pass
    
    return {
        "splunk": {
            "config": STATE["splunk"],
            "health": HEALTH_STATUS["splunk"]
        },
        "elastic": {
            "config": STATE["elastic"],
            "health": HEALTH_STATUS["elastic"]
        }
    }

@router.post("/outputs/dlq/retry")
async def retry_dlq(
    dest: str,
    limit: int = 100,
    request: Request = None
):
    """Retry failed exports from DLQ"""
    # Check authorization
    scopes = getattr(request.state, 'scopes', []) if request else []
    if "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'admin' scope")
    
    if dest not in ["splunk", "elastic"]:
        raise HTTPException(status_code=400, detail="Invalid destination")
    
    # TODO: Implement DLQ retry logic
    # This would read from DLQ files and re-enqueue to export queue
    
    return {
        "status": "not_implemented",
        "message": "DLQ retry functionality not yet implemented"
    }
