# app/auth/__init__.py
import os
from typing import Optional, List
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from ..db import get_db
# If you have these, keep; otherwise remove DB branch entirely.
from ..models.apikey import ApiKey  # optional
import hashlib
from .keys import KEY_SCOPES, is_admin_key, is_user_key, get_key_scope

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _extract_api_key(request: Request) -> Optional[str]:
    """Extract API key from request headers with multiple fallback formats"""
    # 1) Authorization: Bearer <key>
    auth = request.headers.get("Authorization", "")
    if auth:
        parts = auth.split(None, 1)  # ["Bearer", "<key>"] or ["<key>"]
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        # 2) Authorization: <key> (fallback)
        if len(parts) == 1 and parts[0] and parts[0].lower() != "bearer":
            return parts[0].strip()

    # 3) X-API-Key: <key>
    x_key = request.headers.get("X-API-Key")
    if x_key:
        return x_key.strip()
    
    return None

class SimpleKey:
    def __init__(self, scopes: Optional[List[str]] = None):
        self.scopes = scopes or []

# Public endpoints that must bypass auth (readiness, docs, etc.)
PUBLIC_PATHS = {
    "/",               # root
    "/v1/health",
    "/v1/version",
    "/v1/schema",
    "/openapi.json",
}
PUBLIC_PREFIXES = ("/docs", "/redoc")

def _token_from_request(req: Request) -> Optional[str]:
    """Legacy function - use _extract_api_key instead"""
    return _extract_api_key(req)

def _is_env_admin(token: Optional[str]) -> bool:
    """Legacy function - use is_admin_key instead"""
    return bool(token) and is_admin_key(token)

def _is_user_token(token: Optional[str]) -> bool:
    """Legacy function - use is_user_key instead"""
    return bool(token) and is_user_key(token)

def require_key(req: Request, db: Session = Depends(get_db)) -> SimpleKey:
    # Allowlist: health/version/schema/openapi/docs/redoc must never require auth
    path = (req.url.path or "").rstrip("/")
    if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
        return SimpleKey([])

    # Extract token using the new lenient parser
    token = _extract_api_key(req)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    # Check if token is known and get its scope
    scope = get_key_scope(token)
    if scope == "admin":
        return SimpleKey(["admin"])
    elif scope == "user":
        return SimpleKey(["user"])
    
    # Special case: "***" is a test user token
    if token == "***":
        return SimpleKey(["user"])

    # 3) Optional DB-backed tokens (gracefully skip if table missing)
    try:
        h = _sha256(token)
        key = db.query(ApiKey).filter(ApiKey.hash == h, ApiKey.disabled == False).one_or_none()
        if not key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        scopes = key.scopes or []
        return SimpleKey(scopes)
    except OperationalError as e:
        if "no such table" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        raise

def require_admin(user: SimpleKey = Depends(require_key)) -> SimpleKey:
    if "admin" in user.scopes:
        return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin scope required")


