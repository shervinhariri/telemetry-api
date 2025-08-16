"""
Demo API endpoints for Telemetry API
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Dict, Any, Optional
import logging
from ..demo.generator import demo_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Demo"])

@router.post("/demo/start", summary="Start demo generator")
async def start_demo(
    Authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Start the demo event generator.
    
    Requires admin scope. Generates synthetic NetFlow and Zeek events
    at the configured EPS rate for the configured duration.
    """
    # Verify admin scope
    from ..main import require_api_key
    require_api_key(Authorization, required_scopes=["admin"])
    
    try:
        success = await demo_service.start()
        if success:
            status = demo_service.get_status()
            logger.info("Demo generator started via API")
            return {
                "status": "started",
                "message": "Demo generator started successfully",
                "config": status
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to start demo generator")
    except Exception as e:
        logger.error(f"Error starting demo generator: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/demo/stop", summary="Stop demo generator")
async def stop_demo(
    Authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Stop the demo event generator.
    
    Requires admin scope. Stops the currently running demo generator.
    """
    # Verify admin scope
    from ..main import require_api_key
    require_api_key(Authorization, required_scopes=["admin"])
    
    try:
        success = await demo_service.stop()
        if success:
            logger.info("Demo generator stopped via API")
            return {
                "status": "stopped",
                "message": "Demo generator stopped successfully"
            }
        else:
            return {
                "status": "not_running",
                "message": "Demo generator was not running"
            }
    except Exception as e:
        logger.error(f"Error stopping demo generator: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/demo/status", summary="Get demo generator status")
async def get_demo_status(
    Authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Get the current status of the demo generator.
    
    Returns configuration and runtime status information.
    """
    # Verify API key
    from ..main import require_api_key
    require_api_key(Authorization)
    try:
        status = demo_service.get_status()
        return {
            "status": "ok",
            "demo": status
        }
    except Exception as e:
        logger.error(f"Error getting demo status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
