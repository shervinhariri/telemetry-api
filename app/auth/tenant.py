import os
from fastapi import HTTPException, Request
from app.db import SessionLocal
from app.models.tenant import Tenant

DEFAULT_TENANT = os.getenv("DEFAULT_TENANT", "default")

def require_tenant(optional: bool = False):
    async def dep(request: Request):
        scopes = set(getattr(request.state, "scopes", []) or [])
        resolved_tenant_id = None

        with SessionLocal() as db:
            # 1) Header wins if valid (we treat header as tenant_id per schema)
            hdr = request.headers.get("x-tenant-id") or request.headers.get("X-Tenant-ID")
            tenant_row = None
            if hdr:
                tenant_row = db.get(Tenant, hdr)
                if not tenant_row:
                    raise HTTPException(status_code=404, detail="tenant_not_found")
                resolved_tenant_id = tenant_row.tenant_id

            # 2) If no header, use token-bound tenant if present
            if tenant_row is None:
                token_tid = getattr(request.state, "tenant_id", None)
                if token_tid:
                    tenant_row = db.get(Tenant, token_tid)
                    if tenant_row:
                        resolved_tenant_id = tenant_row.tenant_id

            # 3) Admin cross-tenant: fall back to DEFAULT_TENANT if set and exists
            if tenant_row is None and "admin" in scopes:
                if DEFAULT_TENANT:
                    candidate = db.get(Tenant, DEFAULT_TENANT)
                    if candidate:
                        tenant_row = candidate
                        resolved_tenant_id = candidate.tenant_id

            # 4) If still none
            if tenant_row is None:
                if optional:
                    return None
                raise HTTPException(status_code=400, detail="tenant_required")

            # Stash for downstream
            request.state.tenant_id = resolved_tenant_id
            return tenant_row

    return dep


