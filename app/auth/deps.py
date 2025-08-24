from fastapi import Request, HTTPException, status, Depends
import logging
import os
import re
from sqlalchemy.exc import OperationalError
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
    
    with SessionLocal() as db:
        token_hash = hash_token(token)
        try:
            key = db.query(ApiKey).filter(ApiKey.hash == token_hash, ApiKey.disabled == False).first()
        except OperationalError:
            # Table missing in this process? Initialize and retry once.
            init_schema_and_seed_if_needed()
            key = db.query(ApiKey).filter(ApiKey.hash == token_hash, ApiKey.disabled == False).first()
        if not key:
            log.warning("auth: key not found for hash=%s", token_hash)
            raise HTTPException(
                status_code=401, 
                detail={"error": "unauthorized", "hint": "invalid API key or tenant"}
            )
        
        tenant_id = key.tenant_id

        # Check if tenant exists
        tenant = db.get(Tenant, tenant_id)
        if not tenant:
            log.warning("auth: tenant not found for key=%s tenant_id=%s", key.key_id, tenant_id)
            raise HTTPException(
                status_code=401, 
                detail={"error": "unauthorized", "hint": "invalid API key or tenant"}
            )

        # Optional admin override
        override = request.headers.get("X-Tenant-ID")
        if override:
            if "admin" not in (key.scopes or []):
                raise HTTPException(status_code=403, detail="X-Tenant-ID override requires admin scope")
            # ensure target tenant exists
            if not db.get(Tenant, override):
                raise HTTPException(status_code=404, detail="Tenant not found")
            tenant_id = override

        # Attach to request
        request.state.scopes = key.scopes or []
        request.state.tenant_id = tenant_id
        request.state.key_id = key.key_id

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

