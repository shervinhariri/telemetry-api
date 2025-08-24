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
        auth = request.headers.get("authorization","")
        if auth.lower().startswith("bearer "):
            token = auth.split(" ",1)[1].strip()
    
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
                if not row or row.disabled:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
                request.state.scopes = (row.scopes or "").split(",")
                request.state.key_id = row.key_id
                break
        except OperationalError:
            attempts += 1
            if attempts >= 3:
                # degrade to 401 instead of 500
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth backend unavailable")
            time.sleep(0.05)
        
        # For now, use default tenant since we're using raw SQL
        request.state.tenant_id = "default"

# ----- Scope dependency helpers -----
ADMIN_SUPER = {"admin"}

def _norm_scopes(val) -> set:
    if not val:
        return set()
    if isinstance(val, str):
        parts = re.split(r"[\s,]+", val.strip())
        return {p for p in parts if p}
    try:
        return set(val)
    except TypeError:
        return set()

def require_scopes(*allowed: str):
    allowed_set = set(allowed)

    async def dep(request: Request):
        # Optional dev bypass
        if os.getenv("DEV_BYPASS_SCOPES", "false").lower() == "true":
            return True

        token_scopes = _norm_scopes(getattr(request.state, "scopes", []))
        # admin is always enough
        if token_scopes & ADMIN_SUPER:
            return True
        # any one of the allowed scopes is enough
        if token_scopes & allowed_set:
            return True
        log.warning("scope denied: need=%s token=%s", sorted(allowed_set), sorted(token_scopes))
        raise HTTPException(status_code=403, detail="forbidden: missing scope")

    return dep

