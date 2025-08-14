"""
System information endpoint
"""

import time
import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from ..api.version import APP_VERSION, GIT_SHA, IMAGE, DOCKERHUB_TAG
from ..metrics import metrics
from ..pipeline import STATS

router = APIRouter()

@router.get("/system")
async def get_system_info() -> Dict[str, Any]:
    """Get structured system information"""
    try:
        # Get application metrics
        with metrics.lock:
            events_per_second = len(metrics.eps_window) if metrics.eps_window else 0
            queue_depth = metrics.totals.get("queue_depth", 0)
        
        # Get recent errors (last 10)
        recent_errors = []
        # TODO: Implement error tracking
        
        # Calculate uptime
        uptime_seconds = int(time.time() - STATS.get("start_time", time.time()))
        
        return {
            "version": APP_VERSION,
            "git_sha": GIT_SHA,
            "image": f"{IMAGE}:{DOCKERHUB_TAG}",
            "uptime_s": uptime_seconds,
            "workers": 1,  # Single worker for now
            "mem_mb": 0,  # TODO: Implement without psutil
            "mem_pct": 0,  # TODO: Implement without psutil
            "cpu_pct": 0,  # TODO: Implement without psutil
            "eps": events_per_second,
            "queue_depth": queue_depth,
            "last_errors": recent_errors
        }
        
    except Exception as e:
        logging.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system information")
