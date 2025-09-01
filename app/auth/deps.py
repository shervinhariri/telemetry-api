from fastapi import Request, HTTPException, status, Depends
import logging
import os
import re
import time
import json
import hashlib
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models.apikey import ApiKey
from app.models.tenant import Tenant
from app.utils.crypto import hash_token
from app.db_init import init_schema_and_seed_if_needed

log = logging.getLogger("telemetry")

def _parse_scopes(scopes_str: str) -> list:
    """Parse scopes from string, handling both JSON arrays and comma-separated values"""
    if not scopes_str:
        return []
    
    scopes_str = scopes_str.strip()
    
    # Try to parse as JSON first
    try:
        if scopes_str.startswith('[') and scopes_str.endswith(']'):
            json_scopes = json.loads(scopes_str)
            if isinstance(json_scopes, list):
                return [str(s).strip().lower() for s in json_scopes if s]
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Fallback to comma-separated parsing
    parts = re.split(r"[\s,]+", scopes_str)
    return [p.strip().lower() for p in parts if p.strip()]

async def authenticate(request: Request):
    # Ensure schema exists + seed default keys if empty (idempotent, guarded)
    init_schema_and_seed_if_needed()
    
    # Check for API key in various header formats
    token = None
    
    # Try X-API-Key or X-Api-Key headers first
    token = request.headers.get("X-API-Key") or request.headers.get("X-Api-Key")
    
    # Fallback to Authorization header (Bearer or raw token)
    if not token:
        auth = request.headers.get("authorization", "") or request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
        elif auth.strip():  # Also allow raw "Authorization: <token>"
            token = auth.strip()
    
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    
    # DB lookup with retry
    attempts = 0
    while True:
        try:
            with SessionLocal() as db:
                token_hash = hash_token(token)
                row = db.execute(text("SELECT key_id, disabled, scopes FROM api_keys WHERE hash = :h LIMIT 1"),
                                 {"h": token_hash}).fetchone()
                if not row:
                    log.warning("AUTH: token not found in database")
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
                
                if row.disabled:
                    log.warning("AUTH: token disabled, key_id=%s", row.key_id)
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key disabled")
                
                # Parse scopes properly
                scopes_list = _parse_scopes(row.scopes or "")
                request.state.scopes = scopes_list
                request.state.key_id = row.key_id
                request.state.tenant_id = "default"  # For now, use default tenant
                
                log.info("AUTH: token matched, key_id=%s, scopes=%s", row.key_id, scopes_list)
                break
                
        except OperationalError as e:
            attempts += 1
            if attempts >= 3:
                log.error("AUTH: DB operational error after %d attempts: %s", attempts, e)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth backend unavailable")
            time.sleep(0.05)

# ----- Scope dependency helpers -----
ADMIN_SUPER = {"admin"}

def _norm_scopes(val) -> set:
    if not val:
        return set()
    if isinstance(val, str):
        parts = re.split(r"[\s,]+", val.strip())
        return {p.lower() for p in parts if p}
    try:
        return {str(s).lower() for s in val}
    except TypeError:
        return set()

def require_scopes(*allowed: str):
    allowed_set = {s.lower() for s in allowed}

    async def dep(request: Request):
        # Optional dev bypass
        if os.getenv("DEV_BYPASS_SCOPES", "false").lower() == "true":
            return True

        token_scopes = _norm_scopes(getattr(request.state, "scopes", []))
        
        # Check for wildcard scope
        if "*" in token_scopes:
            log.info("AUTH: scope allowed by wildcard (*), required=%s, token=%s", sorted(allowed_set), sorted(token_scopes))
            return True
            
        # admin is always enough
        if token_scopes & ADMIN_SUPER:
            log.info("AUTH: scope allowed by admin, required=%s, token=%s", sorted(allowed_set), sorted(token_scopes))
            return True
            
        # any one of the allowed scopes is enough
        if token_scopes & allowed_set:
            log.info("AUTH: scope allowed by specific scope, required=%s, token=%s", sorted(allowed_set), sorted(token_scopes))
            return True
            
        log.warning("AUTH: scope denied, need=%s token=%s", sorted(allowed_set), sorted(token_scopes))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden: missing scope")

    return dep

def require_admin():
    """Require admin scope specifically"""
    return require_scopes("admin")

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _norm_scopes_list(scopes) -> list:
    if scopes is None:
        return []
    if isinstance(scopes, list):
        return scopes
    if isinstance(scopes, str):
        try:
            val = json.loads(scopes)
            return val if isinstance(val, list) else []
        except Exception:
            return []
    return []

# New auth functions for multiple header format support
def _extract_token(req: Request) -> str:
    # Authorization: Bearer <token>   OR   Authorization: <token>
    auth = req.headers.get("authorization") or req.headers.get("Authorization")
    if auth:
        parts = auth.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        if len(parts) == 1:
            return parts[0]
    # X-API-Key: <token>
    x = req.headers.get("x-api-key") or req.headers.get("X-API-Key")
    if x:
        return x.strip()
    return ""

def require_key(req: Request, db: Session = Depends(get_db)) -> ApiKey:
    token = _extract_token(req)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    h = _sha256(token)
    key = db.query(ApiKey).filter(ApiKey.hash == h, ApiKey.disabled == False).one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    key._norm_scopes = _norm_scopes_list(key.scopes)
    return key

def require_admin_new(key: ApiKey = Depends(require_key)) -> ApiKey:
    scopes = getattr(key, "_norm_scopes", _norm_scopes_list(key.scopes))
    if "admin" not in scopes and "*" not in scopes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin scope required")
    return key

