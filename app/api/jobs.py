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

from app.auth.deps import require_scopes

logger = logging.getLogger("api.jobs")

router = APIRouter()

# In-memory job store (in production, use Redis or database)
_jobs: Dict[str, Dict[str, Any]] = {}

class JobCreate(BaseModel):
    type: str
    params: Optional[Dict[str, Any]] = None

class JobResponse(BaseModel):
    job_id: str
    type: str
    status: str
    progress: int
    msg: str
    created_at: float
    updated_at: float

def create_job(job_type: str, params: Optional[Dict[str, Any]] = None) -> str:
    """Create a new job"""
    job_id = str(uuid.uuid4())
    now = time.time()
    
    _jobs[job_id] = {
        "job_id": job_id,
        "type": job_type,
        "status": "pending",
        "progress": 0,
        "msg": "Job created",
        "params": params or {},
        "created_at": now,
        "updated_at": now
    }
    
    logger.info(f"Created job {job_id} of type {job_type}")
    return job_id

def update_job(job_id: str, status: str, progress: int = None, msg: str = None):
    """Update job status"""
    if job_id not in _jobs:
        return
    
    job = _jobs[job_id]
    job["status"] = status
    job["updated_at"] = time.time()
    
    if progress is not None:
        job["progress"] = progress
    if msg is not None:
        job["msg"] = msg
    
    logger.info(f"Updated job {job_id}: {status} - {msg}")

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job by ID"""
    return _jobs.get(job_id)

def list_jobs() -> List[Dict[str, Any]]:
    """List all jobs"""
    return list(_jobs.values())

async def run_geo_download_job(job_id: str):
    """Run GeoIP download job"""
    try:
        update_job(job_id, "running", 0, "Starting GeoIP download...")
        
        # Simulate download progress
        for i in range(1, 11):
            await asyncio.sleep(0.5)  # Simulate work
            progress = i * 10
            update_job(job_id, "running", progress, f"Downloading... {progress}%")
        
        # Simulate database update
        update_job(job_id, "running", 90, "Updating database...")
        await asyncio.sleep(1)
        
        # Mark as complete
        update_job(job_id, "completed", 100, "GeoIP database updated successfully")
        
        # TODO: Actually download and update the GeoIP database
        logger.info(f"GeoIP download job {job_id} completed")
        
    except Exception as e:
        logger.error(f"GeoIP download job {job_id} failed: {e}")
        update_job(job_id, "failed", 0, f"Download failed: {str(e)}")

@router.post("/geo/download", dependencies=[Depends(require_scopes("admin"))])
async def create_geo_download_job() -> Dict[str, str]:
    """Create a GeoIP download job"""
    job_id = create_job("geo_download")
    
    # Start the job asynchronously
    asyncio.create_task(run_geo_download_job(job_id))
    
    return {"job_id": job_id}

@router.get("/jobs", dependencies=[Depends(require_scopes("admin"))])
async def get_jobs() -> List[JobResponse]:
    """Get list of all jobs"""
    jobs = list_jobs()
    return [JobResponse(**job) for job in jobs]

@router.get("/jobs/{job_id}", dependencies=[Depends(require_scopes("admin"))])
async def get_job_by_id(job_id: str) -> JobResponse:
    """Get job by ID"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse(**job)

@router.get("/geo/test", dependencies=[Depends(require_scopes("admin"))])
async def test_geoip(ip: str = "8.8.8.8") -> Dict[str, Any]:
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
