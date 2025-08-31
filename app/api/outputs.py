from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, AnyHttpUrl, Field, model_validator
from typing import List, Optional, Dict, Any
import time
import httpx
import asyncio
import uuid
from ..auth.deps import require_scopes
from ..services.prometheus_metrics import prometheus_metrics
from ..metrics import record_export_test
from ..dlq import dlq
import json

router = APIRouter()

class SplunkConfig(BaseModel):
    url: str = Field(..., description="Splunk HEC URL")
    token: str = Field(..., description="Splunk HEC token")
    verify_tls: bool = Field(True, description="Verify TLS certificates")
    batch_max: int = Field(1000, ge=1, le=5000, description="Maximum batch size")
    retries: int = Field(3, ge=0, le=5, description="Number of retries")
    timeout_sec: int = Field(10, ge=1, le=30, description="Timeout in seconds")
    
    @model_validator(mode='after')
    def validate_url(self) -> 'SplunkConfig':
        if not self.url:
            raise ValueError("URL is required")
        if not self.url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        if ' ' in self.url:
            raise ValueError("URL cannot contain spaces")
        # Normalize trailing slashes
        self.url = self.url.rstrip('/')
        return self
    
    @model_validator(mode='after')
    def validate_token(self) -> 'SplunkConfig':
        if not self.token or not self.token.strip():
            raise ValueError("Token is required and cannot be empty")
        return self

class ElasticConfig(BaseModel):
    url: str = Field(..., description="Elasticsearch URL")
    index: str = Field(..., description="Elasticsearch index pattern")
    verify_tls: bool = Field(True, description="Verify TLS certificates")
    batch_max: int = Field(1000, ge=1, le=5000, description="Maximum batch size")
    retries: int = Field(3, ge=0, le=5, description="Number of retries")
    timeout_sec: int = Field(10, ge=1, le=30, description="Timeout in seconds")
    username: Optional[str] = Field(None, description="Elasticsearch username")
    password: Optional[str] = Field(None, description="Elasticsearch password")
    api_key: Optional[str] = Field(None, description="Elasticsearch API key")
    
    @model_validator(mode='after')
    def validate_url(self) -> 'ElasticConfig':
        if not self.url:
            raise ValueError("URL is required")
        if not self.url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        if ' ' in self.url:
            raise ValueError("URL cannot contain spaces")
        # Normalize trailing slashes
        self.url = self.url.rstrip('/')
        return self
    
    @model_validator(mode='after')
    def validate_index(self) -> 'ElasticConfig':
        if not self.index or not self.index.strip():
            raise ValueError("Index is required and cannot be empty")
        return self

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

@router.post("/outputs/splunk")
@router.put("/outputs/splunk")
def set_splunk(cfg: SplunkConfig):
    try:
        STATE["splunk"] = cfg.model_dump()
        return {"status": "ok", "splunk": STATE["splunk"]}
    except ValueError as e:
        return JSONResponse(
            status_code=422, 
            content={"status": "error", "field": "validation", "reason": str(e)}
        )

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
        return {"status": "ok", "elastic": STATE["elastic"]}
    except ValueError as e:
        return JSONResponse(
            status_code=422, 
            content={"status": "error", "field": "validation", "reason": str(e)}
        )

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

@router.post("/outputs/test")
async def test_output(request: TestOutputRequest, req: Request):
    """Test output connectivity with unified response format"""
    # Check authorization
    scopes = getattr(req.state, 'scopes', [])
    if "export" not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'export' or 'admin' scope")
    
    if request.target not in ["splunk", "elastic"]:
        return JSONResponse(
            status_code=422,
            content={"status": "error", "field": "target", "reason": "Target must be 'splunk' or 'elastic'"}
        )
    
    t0 = time.perf_counter()
    
    if request.target == "splunk":
        ok, http_status, error, bytes_sent = await test_splunk_send()
    else:  # elastic
        ok, http_status, error, bytes_sent = await test_elastic_send()
    
    duration_ms = int((time.perf_counter() - t0) * 1000)
    
    # Update metrics
    from ..metrics import record_outputs_test_success, record_outputs_test_fail
    if ok:
        record_outputs_test_success(request.target)
    else:
        record_outputs_test_fail(request.target)
    
    # Update health status
    if ok:
        HEALTH_STATUS[request.target]["reachable"] = True
        HEALTH_STATUS[request.target]["last_success_ts"] = time.time()
        HEALTH_STATUS[request.target]["last_http_code"] = http_status
        HEALTH_STATUS[request.target]["last_error"] = None
    else:
        HEALTH_STATUS[request.target]["reachable"] = False
        HEALTH_STATUS[request.target]["last_http_code"] = http_status
        HEALTH_STATUS[request.target]["last_error"] = error
    
    return {
        "target": request.target,
        "http_status": http_status or 0,
        "duration_ms": duration_ms,
        "bytes": bytes_sent,
        "error": error,
        "request_id": str(uuid.uuid4())
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
