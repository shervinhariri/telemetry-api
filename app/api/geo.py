from fastapi import APIRouter
from typing import Dict, Any
import time
import uuid

router = APIRouter(prefix="/v1", tags=["geo"])

_JOBS: Dict[str, Dict[str, Any]] = {}

@router.post("/geo/download")
def geo_download() -> Dict[str, Any]:
    job_id = f"geo-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    _JOBS[job_id] = {"id": job_id, "type": "geo-download", "status": "queued", "created_at": time.time()}
    return {"status": "ok", "job_id": job_id}

@router.get("/jobs")
def list_jobs() -> Dict[str, Any]:
    return {"status": "ok", "jobs": list(_JOBS.values())}
