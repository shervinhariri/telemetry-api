from fastapi import Request, HTTPException, status, Depends
import logging
import os
import re
import time
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
from app.db import SessionLocal
from app.models.apikey import ApiKey
from app.models.tenant import Tenant
from app.utils.crypto import hash_token
from app.db_init import init_schema_and_seed_if_needed

log = logging.getLogger("telemetry")

async def authenticate(request: Request):
    # Ensure schema exists + seed default keys if empty (idempotent, guarded)
    init_schema_and_seed_if_needed()
    
    # Check for API key in various header formats
    token = None
    
    # Try X-API-Key or X-Api-Key headers first
    token = request.headers.get("X-API-Key") or request.headers.get("X-Api-Key")
    
    # Fallback to Authorization Bearer header
    if not token:
        auth = request.headers.get("authorization", "") or request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
    
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
                scopes_str = row.scopes or ""
                scopes_list = [s.strip().lower() for s in scopes_str.split(",") if s.strip()]
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

