"""
API Key Management Endpoints
"""
from fastapi import APIRouter, HTTPException, Header, Response
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging

from ..auth import (
    validate_api_key, create_api_key, delete_api_key, 
    list_api_keys, rotate_api_key, get_available_scopes
)

router = APIRouter()

class CreateKeyRequest(BaseModel):
    scopes: List[str]
    note: str = ""

class CreateKeyResponse(BaseModel):
    key_id: str
    api_key: str
    scopes: List[str]
    note: str
    created_at: str

class RotateKeyResponse(BaseModel):
    key_id: str
    api_key: str
    scopes: List[str]
    note: str
    rotated_at: str

def require_admin_scope(Authorization: Optional[str] = Header(None)):
    """Require admin scope for key management"""
    if not Authorization or not Authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    api_key = Authorization[7:]  # Remove "Bearer "
    key_data = validate_api_key(api_key, required_scopes=["admin"])
    
    if not key_data:
        raise HTTPException(status_code=403, detail="Admin scope required")

@router.post("/keys", response_model=CreateKeyResponse)
async def create_key(
    request: CreateKeyRequest,
    response: Response,
    Authorization: Optional[str] = Header(None)
):
    """Create a new API key with specified scopes (admin only)"""
    require_admin_scope(Authorization)
    
    # Validate scopes
    available_scopes = get_available_scopes()
    for scope in request.scopes:
        if scope not in available_scopes:
            raise HTTPException(status_code=400, detail=f"Invalid scope: {scope}")
    
    # Create the key
    key_data = create_api_key(
        scopes=request.scopes,
        note=request.note,
        created_by="admin"  # In production, get from auth context
    )
    
    response.headers["X-API-Version"] = "1.0.0"
    
    return CreateKeyResponse(**key_data)

@router.get("/keys")
async def list_keys(
    response: Response,
    Authorization: Optional[str] = Header(None)
):
    """List all API keys (admin only)"""
    require_admin_scope(Authorization)
    
    keys = list_api_keys()
    
    response.headers["X-API-Version"] = "1.0.0"
    
    return {
        "keys": keys,
        "total": len(keys)
    }

@router.delete("/keys/{key_id}")
async def delete_key(
    key_id: str,
    response: Response,
    Authorization: Optional[str] = Header(None)
):
    """Delete an API key (admin only)"""
    require_admin_scope(Authorization)
    
    if delete_api_key(key_id):
        response.headers["X-API-Version"] = "1.0.0"
        return {"status": "deleted", "key_id": key_id}
    else:
        raise HTTPException(status_code=404, detail="API key not found")

@router.post("/keys/{key_id}/rotate", response_model=RotateKeyResponse)
async def rotate_key(
    key_id: str,
    response: Response,
    Authorization: Optional[str] = Header(None)
):
    """Rotate an API key (admin only)"""
    require_admin_scope(Authorization)
    
    rotated_key = rotate_api_key(key_id)
    if rotated_key:
        response.headers["X-API-Version"] = "1.0.0"
        return RotateKeyResponse(**rotated_key)
    else:
        raise HTTPException(status_code=404, detail="API key not found")

@router.get("/keys/scopes")
async def get_scopes(response: Response):
    """Get available scopes (no auth required)"""
    scopes = get_available_scopes()
    
    response.headers["X-API-Version"] = "1.0.0"
    
    return {
        "scopes": scopes,
        "total": len(scopes)
    }
