"""
System information endpoint
"""

import time
import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List

from ..api.version import GIT_SHA, IMAGE, DOCKERHUB_TAG
from ..metrics import metrics
from ..pipeline import STATS
from ..config import FEATURES
from ..queue_manager import queue_manager

from app.auth.deps import require_scopes

router = APIRouter()

@router.get("/system", dependencies=[Depends(require_scopes("admin"))])
async def get_system_info() -> Dict[str, Any]:
    """Get structured system information"""
    try:
        # Get application metrics
        with metrics.lock:
            events_per_second = len(metrics.eps_window) if metrics.eps_window else 0
        
        # Get queue statistics from queue manager
        queue_stats = queue_manager.get_queue_stats()
        queue_depth = queue_stats["depth"]
        
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
        backpressure = queue_stats["saturation"] > 0.8  # 80% saturation threshold
        if dlq_stats["total_events"] > 10000:  # High DLQ size
            backpressure = True
        
        from ..api.version import get_version_from_file
        version = get_version_from_file()
        
        # Build features dict with UDP head status
        features = FEATURES.copy()
        features["udp_head"] = "ready" if FEATURES.get("udp_head", False) else "disabled"
        
        return {
            "status": "ok",
            "version": version,
            "git_sha": GIT_SHA,
            "image": f"{IMAGE}:{version}",
            "features": features,
            "uptime_s": uptime_seconds,
            "workers": queue_manager.worker_pool_size,
            "mem_mb": 0,  # TODO: Implement without psutil
            "mem_pct": 0,  # TODO: Implement without psutil
            "cpu_pct": 0,  # TODO: Implement without psutil
            "eps": events_per_second,
            "queue": queue_stats,
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
            "version": version,
            "git_sha": GIT_SHA,
            "image": f"{IMAGE}:{version}",
            "uptime_s": 0,
            "workers": 0,
            "eps": 0,
            "queue": {"depth": 0, "max": 0, "saturation": 0.0},
            "backpressure": False,
            "dlq": {"total_events": 0, "files": 0},
            "idempotency": {"keys": 0, "hits": 0},
            "last_errors": []
        }
