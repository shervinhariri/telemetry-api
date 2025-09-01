"""
Jobs API for managing background tasks
"""

import uuid
import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from threading import RLock
from datetime import datetime

from ..auth import require_admin

logger = logging.getLogger("api.jobs")

router = APIRouter()

# In-memory job store with thread safety
_jobs: List[Dict[str, Any]] = []
_lock = RLock()

class JobCreate(BaseModel):
    type: str
    params: Optional[Dict[str, Any]] = None

class JobResponse(BaseModel):
    id: str
    type: str
    status: str
    created_at: str

def create_job(job_type: str, meta: Optional[Dict[str, Any]] = None) -> str:
    """Create a new job"""
    job_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"
    
    job = {
        "id": job_id,
        "type": job_type,
        "status": "queued",
        "created_at": now,
        **({"meta": meta} if meta else {}),
    }
    
    with _lock:
        _jobs.append(job)
    
    logger.info(f"Created job {job_id} of type {job_type}")
    return job_id

def set_job_status(job_id: str, status: str):
    """Update job status"""
    with _lock:
        for j in _jobs:
            if j["id"] == job_id:
                j["status"] = status
                return

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job by ID"""
    with _lock:
        for job in _jobs:
            if job["id"] == job_id:
                return job
    return None

def list_jobs() -> List[Dict[str, Any]]:
    """List all jobs"""
    with _lock:
        return list(_jobs)

async def run_geo_download_job(job_id: str):
    """Run GeoIP download job"""
    try:
        set_job_status(job_id, "running")
        
        # Simulate download progress
        for i in range(1, 11):
            await asyncio.sleep(0.5)  # Simulate work
            progress = i * 10
            logger.info(f"GeoIP download progress: {progress}%")
        
        # Simulate database update
        set_job_status(job_id, "running")
        await asyncio.sleep(1)
        
        # Mark as complete
        set_job_status(job_id, "completed")
        
        # TODO: Actually download and update the GeoIP database
        logger.info(f"GeoIP download job {job_id} completed")
        
    except Exception as e:
        logger.error(f"GeoIP download job {job_id} failed: {e}")
        set_job_status(job_id, "failed")

@router.post("/geo/download")
async def create_geo_download_job(_: Any = Depends(require_admin)) -> Dict[str, str]:
    """Create a GeoIP download job"""
    job_id = create_job("geo_download")
    
    # Start the job asynchronously
    asyncio.create_task(run_geo_download_job(job_id))
    
    return {"job_id": job_id}

@router.get("/jobs")
async def get_jobs(_: Any = Depends(require_admin)) -> List[JobResponse]:
    """Get list of all jobs"""
    jobs = list_jobs()
    return [JobResponse(**job) for job in jobs]

@router.get("/jobs/{job_id}")
async def get_job_by_id(job_id: str, _: Any = Depends(require_admin)) -> JobResponse:
    """Get job by ID"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse(**job)

@router.get("/geo/test")
async def test_geoip(ip: str = "8.8.8.8", _: Any = Depends(require_admin)) -> Dict[str, Any]:
    """Test GeoIP lookup for an IP address"""
    from ..enrich.geo import geoip_loader, asn_loader
    
    result = {
        "ip": ip,
        "geo": None,
        "asn": None
    }
    
    # Test GeoIP lookup
    geo_data = geoip_loader.lookup(ip)
    if geo_data:
        result["geo"] = geo_data
    
    # Test ASN lookup
    asn_data = asn_loader.lookup(ip)
    if asn_data:
        result["asn"] = asn_data
    
    return result
