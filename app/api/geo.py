from fastapi import APIRouter
from typing import Dict, Any, List
import time, uuid

router = APIRouter(prefix="/v1", tags=["geo"])

_JOBS: Dict[str, Dict[str, Any]] = {}

@router.post("/geo/download")
def geo_download() -> Dict[str, Any]:
    job_id = f"geo-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    _JOBS[job_id] = {
        "id": job_id,
        "type": "geo_download",      # <- underscore, not hyphen
        "status": "queued",
        "created_at": time.time(),
    }
    return {"status": "ok", "job_id": job_id}

@router.get("/jobs")
def list_jobs() -> List[Dict[str, Any]]:
    return list(_JOBS.values())      # <- bare list, not wrapped
