"""
System information endpoint
"""

import time
import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List

from ..api.version import APP_VERSION, GIT_SHA, IMAGE, DOCKERHUB_TAG
from ..metrics import metrics
from ..pipeline import STATS
from ..config import FEATURES

from app.auth.deps import require_scopes

router = APIRouter()

@router.get("/system", dependencies=[Depends(require_scopes("admin"))])
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
        
        # Get DLQ statistics
        from ..dlq import dlq
        dlq_stats = dlq.get_dlq_stats()
        
        # Get idempotency statistics
        from ..idempotency import get_idempotency_stats
        idempotency_stats = get_idempotency_stats()
        
        # Check for backpressure conditions
        backpressure = False
        if queue_depth > 5000:  # High queue depth
            backpressure = True
        if dlq_stats["total_events"] > 10000:  # High DLQ size
            backpressure = True
        
        return {
            "status": "ok",
            "version": APP_VERSION,
            "git_sha": GIT_SHA,
            "image": f"{IMAGE}:{DOCKERHUB_TAG}" if DOCKERHUB_TAG and DOCKERHUB_TAG != "unknown" else f"{IMAGE}:{APP_VERSION}",
            "features": FEATURES,
            "uptime_s": uptime_seconds,
            "workers": 1,  # Single worker for now
            "mem_mb": 0,  # TODO: Implement without psutil
            "mem_pct": 0,  # TODO: Implement without psutil
            "cpu_pct": 0,  # TODO: Implement without psutil
            "eps": events_per_second,
            "queue_depth": queue_depth,
            "backpressure": backpressure,
            "dlq": dlq_stats,
            "idempotency": idempotency_stats,
            "last_errors": recent_errors
        }
        
    except Exception as e:
        logging.error(f"Failed to get system info: {e}")
        return {
            "status": "degraded",
            "warn": "System information unavailable",
            "version": APP_VERSION,
            "git_sha": GIT_SHA,
            "image": f"{IMAGE}:{DOCKERHUB_TAG}" if DOCKERHUB_TAG and DOCKERHUB_TAG != "unknown" else f"{IMAGE}:{APP_VERSION}",
            "uptime_s": 0,
            "workers": 0,
            "eps": 0,
            "queue_depth": 0,
            "backpressure": False,
            "dlq": {"total_events": 0, "files": 0},
            "idempotency": {"keys": 0, "hits": 0},
            "last_errors": []
        }
