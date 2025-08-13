from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, AnyHttpUrl, Field
from typing import List, Optional, Dict, Any

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
    urls: List[AnyHttpUrl] = Field(..., min_items=1)
    index_prefix: str = "telemetry-"
    bulk_size: int = 1000
    max_retries: int = 5
    backoff_ms: int = 200
    pipeline: Optional[str] = None
    verify_tls: bool = True

STATE: Dict[str, Any] = {
    "splunk": None,
    "elastic": None,
}

@router.post("/outputs/splunk")
@router.put("/outputs/splunk")
def set_splunk(cfg: SplunkConfig):
    STATE["splunk"] = cfg.model_dump()
    return {"status": "ok", "splunk": STATE["splunk"]}

@router.get("/outputs/splunk")
def get_splunk():
    return {"splunk": STATE["splunk"]}

@router.post("/outputs/elastic")
@router.put("/outputs/elastic")
def set_elastic(cfg: ElasticConfig):
    STATE["elastic"] = cfg.model_dump()
    return {"status": "ok", "elastic": STATE["elastic"]}

@router.get("/outputs/elastic")
def get_elastic():
    return {"elastic": STATE["elastic"]}
