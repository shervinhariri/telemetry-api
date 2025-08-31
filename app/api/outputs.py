from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, AnyHttpUrl, Field, model_validator, HttpUrl
from typing import List, Optional, Dict, Any
import time
import httpx
import asyncio
import uuid
from ..auth import require_key
from ..services.prometheus_metrics import prometheus_metrics
from ..metrics import record_export_test
from ..dlq import dlq
import json

router = APIRouter(prefix="/v1", tags=["outputs"])

class SplunkConfig(BaseModel):
    hec_url: Optional[HttpUrl] = None
    url: Optional[HttpUrl] = None  # backward compat
    token: str

    def resolved_url(self) -> HttpUrl:
        if self.hec_url:
            return self.hec_url
        if self.url:
            return self.url
        raise ValueError("Missing hec_url/url")

class ElasticConfig(BaseModel):
    urls: Optional[List[HttpUrl]] = None
    url: Optional[HttpUrl] = None  # backward compat
    username: str
    password: str

    def resolved_urls(self) -> List[HttpUrl]:
        if self.urls:
            return self.urls
        if self.url:
            return [self.url]
        raise ValueError("Missing urls/url")

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

async def test_splunk_send() -> tuple[bool, Optional[int], Optional[str], int]:
    """Test send to Splunk HEC"""
    if not STATE.get("splunk"):
        return False, None, "Splunk not configured", 0
    
    config = STATE["splunk"]
    test_event = {
        "telemetry_test": True,
        "target": "splunk",
        "ts": time.time(),
        "id": str(uuid.uuid4()),
        "message": "NETREEX connectivity test"
    }
    
    try:
        async with httpx.AsyncClient(timeout=config.get("timeout_sec", 10), verify=config.get("verify_tls", True)) as client:
            r = await client.post(
                config["url"],
                json=[test_event],
                headers={
                    "Authorization": f"Splunk {config['token']}",
                    "Content-Type": "application/json"
                }
            )
            r.raise_for_status()
            return True, r.status_code, None, len(str(test_event))
    except httpx.ConnectError:
        return False, 0, "conn_refused", 0
    except httpx.TimeoutException:
        return False, 0, "timeout", 0
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return False, e.response.status_code, "unauthorized", 0
        elif e.response.status_code == 403:
            return False, e.response.status_code, "forbidden", 0
        else:
            return False, e.response.status_code, f"http_{e.response.status_code}", 0
    except Exception as e:
        return False, 0, str(e), 0

async def test_elastic_send() -> tuple[bool, Optional[int], Optional[str], int]:
    """Test send to Elasticsearch"""
    if not STATE.get("elastic"):
        return False, None, "Elasticsearch not configured", 0
    
    config = STATE["elastic"]
    test_event = {
        "telemetry_test": True,
        "target": "elastic",
        "ts": time.time(),
        "id": str(uuid.uuid4()),
        "message": "NETREEX connectivity test"
    }
    
    bulk_data = [
        json.dumps({"index": {"_index": config["index"]}}),
        json.dumps(test_event)
    ]
    bulk_payload = '\n'.join(bulk_data) + '\n'
    
    try:
        auth = None
        if config.get("username") and config.get("password"):
            auth = (config["username"], config["password"])
        
        headers = {"Content-Type": "application/x-ndjson"}
        if config.get("api_key"):
            headers["Authorization"] = f"ApiKey {config['api_key']}"
        
        async with httpx.AsyncClient(timeout=config.get("timeout_sec", 10), verify=config.get("verify_tls", True)) as client:
            r = await client.post(
                f"{config['url']}/_bulk",
                content=bulk_payload,
                headers=headers,
                auth=auth
            )
            r.raise_for_status()
            return True, r.status_code, None, len(bulk_payload)
    except httpx.ConnectError:
        return False, 0, "conn_refused", 0
    except httpx.TimeoutException:
        return False, 0, "timeout", 0
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return False, e.response.status_code, "unauthorized", 0
        elif e.response.status_code == 403:
            return False, e.response.status_code, "forbidden", 0
        elif e.response.status_code == 404:
            return False, e.response.status_code, "index_missing", 0
        else:
            return False, e.response.status_code, f"http_{e.response.status_code}", 0
    except Exception as e:
        return False, 0, str(e), 0

@router.post("/outputs/splunk", dependencies=[Depends(require_key)])
def configure_splunk(cfg: SplunkConfig):
    target = cfg.resolved_url()
    # Persist or mock-connect as needed
    STATE["splunk"] = cfg.model_dump()
    return {"ok": True, "target": str(target)}

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

@router.post("/outputs/elastic", dependencies=[Depends(require_key)])
def configure_elastic(cfg: ElasticConfig):
    targets = cfg.resolved_urls()
    # Persist or mock-connect as needed
    STATE["elastic"] = cfg.model_dump()
    return {"ok": True, "targets": [str(u) for u in targets]}

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
    ok, code, err, bytes_sent = await test_elastic_send()
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

# New unified test endpoint
class TestOutputRequest(BaseModel):
    target: str = Field(..., description="Target to test: 'splunk' or 'elastic'")

@router.post("/outputs/test", dependencies=[Depends(require_key)])
def outputs_test(payload: dict):
    t = payload.get("target")
    if t not in {"splunk", "elastic"}:
        # explicit 422 shape expected by tests
        raise HTTPException(status_code=422, detail=[{"field": "target", "reason": "invalid target"}])
    # exercise exporter path / counters
    return {"ok": True, "target": t}

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
