"""
Admin Feature Flags API endpoints for runtime configuration management
"""

from fastapi import APIRouter, HTTPException, Request, Depends
import logging
from typing import Dict, Any

from ..config import runtime_config
from ..services.audit import log_admin_action, get_recent_audit_logs
from ..auth import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

@router.get("/featureflags")
async def get_feature_flags(request: Request):
    """Get current feature flags (admin only)"""
    try:
        return runtime_config.get_all()
    except Exception as e:
        logger.error(f"Feature flags get error: {e}")
        return {"error": str(e), "flags": {"ADMISSION_HTTP_ENABLED": False}}

@router.patch("/featureflags")
async def update_feature_flags(request: Request):
    """Update feature flags (admin only)"""
    try:
        payload = await request.json()
        
        # Get API key ID and client info for audit logging
        api_key_id = getattr(request.state, 'api_key_id', 'unknown')
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get('user-agent')
        
        # Get before state
        before_state = runtime_config.get_all()
        
        # Update flags in memory (not persisted to disk)
        runtime_config.update(payload)
        
        # Get after state
        after_state = runtime_config.get_all()
        
        # Log each changed flag
        for flag_name, new_value in payload.items():
            if flag_name in before_state and before_state[flag_name] != new_value:
                log_admin_action(
                    actor_key_id=api_key_id,
                    action="feature_flag_update",
                    target=flag_name,
                    before_value={flag_name: before_state[flag_name]},
                    after_value={flag_name: new_value},
                    client_ip=client_ip,
                    user_agent=user_agent
                )
        
        # Return current state
        return after_state
        
    except Exception as e:
        logger.error(f"Feature flags update error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid feature flags payload: {str(e)}")

@router.get("/audit")
async def get_audit_logs(request: Request, limit: int = 100):
    """Get recent admin audit logs (admin only)"""
    try:
        logs = get_recent_audit_logs(limit=min(limit, 1000))  # Cap at 1000
        return {"audit_logs": logs, "count": len(logs)}
    except Exception as e:
        logger.error(f"Audit logs get error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit logs: {str(e)}")
