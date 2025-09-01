from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from app.db import SessionLocal, engine
from app.auth.deps import require_scopes

from app.schemas.source import (
    SourceCreate, SourceResponse, SourceListResponse, SourceMetrics, SourceStatus
)
from app.services.sources import SourceService
from app.models.source import Source

router = APIRouter()


def _ensure_sources_table():
    """Ensure sources table exists, create if missing"""
    try:
        with engine.begin() as conn:
            # Check if sources table exists
            result = conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table' AND name='sources'").fetchone()
            if not result:
                # Create sources table with minimal schema
                conn.exec_driver_sql("""
                    CREATE TABLE sources (
                        id VARCHAR(64) PRIMARY KEY,
                        tenant_id VARCHAR(64) NOT NULL,
                        type VARCHAR(32) NOT NULL,
                        origin VARCHAR(32),
                        display_name VARCHAR(128) NOT NULL,
                        collector VARCHAR(64) NOT NULL,
                        site VARCHAR(64),
                        tags TEXT,
                        health_status VARCHAR(32) DEFAULT 'stale',
                        last_seen TIMESTAMP,
                        notes TEXT,
                        status VARCHAR(32) NOT NULL DEFAULT 'enabled',
                        allowed_ips TEXT NOT NULL DEFAULT '[]',
                        max_eps INTEGER NOT NULL DEFAULT 0,
                        block_on_exceed BOOLEAN NOT NULL DEFAULT 1,
                        enabled BOOLEAN NOT NULL DEFAULT 1,
                        eps_cap INTEGER NOT NULL DEFAULT 0,
                        last_seen_ts INTEGER,
                        eps_1m REAL,
                        error_pct_1m REAL,
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL
                    )
                """)
                
                # Insert default sources
                import time
                now = int(time.time())
                default_sources = [
                    ("default-http", "default", "http", "http", "Default HTTP Source", "api", "HQ", "[]", "healthy", None, "Default HTTP ingest source", "enabled", "[]", 0, 1, 1, 0, now, 0.0, 0.0, now, now),
                    ("default-udp", "default", "udp", "udp", "Default UDP Source", "udp_head", "HQ", "[]", "healthy", None, "Default UDP ingest source", "enabled", "[]", 0, 1, 1, 0, now, 0.0, 0.0, now, now)
                ]
                
                for source_data in default_sources:
                    conn.exec_driver_sql("""
                        INSERT INTO sources (
                            id, tenant_id, type, origin, display_name, collector, site, tags, 
                            health_status, last_seen, notes, status, allowed_ips, max_eps, 
                            block_on_exceed, enabled, eps_cap, last_seen_ts, eps_1m, 
                            error_pct_1m, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, source_data)
    except Exception as e:
        # Log but don't fail - this is a fallback
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to ensure sources table: {e}")


@router.post("/sources", response_model=SourceResponse)
async def create_source(
    source_data: SourceCreate,
    request: Request
):
    """Create a new source"""
    # Check if user has admin scope
    scopes = getattr(request.state, 'scopes', [])
    tenant_id = getattr(request.state, 'tenant_id', 'default')
    
    if "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Admin scope required")
    
    # Check if source already exists
    db = SessionLocal()
    try:
        existing = SourceService.get_source_by_id(db, source_data.id, tenant_id)
        if existing:
            raise HTTPException(status_code=409, detail="Source already exists")
        
        source = SourceService.create_source(db, source_data, tenant_id)
        return SourceResponse(**source.to_dict())
    finally:
        db.close()


@router.get("/sources", response_model=SourceListResponse, dependencies=[Depends(require_scopes("read_sources"))])
async def list_sources(
    request: Request,
    tenant: Optional[str] = Query(None, description="Filter by tenant"),
    type: Optional[str] = Query(None, description="Filter by source type (udp, http)"),
    status: Optional[str] = Query(None, description="Filter by status (enabled, disabled)"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    site: Optional[str] = Query(None, description="Filter by site"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="Alias for page size")
):
    """Get paginated list of sources"""
    
    # Use tenant from auth if not specified
    tenant_id = tenant or getattr(request.state, 'tenant_id', 'default')
    
    db = SessionLocal()
    try:
        eff_size = page_size or size
        
        # Try to get sources, but handle missing table gracefully
        try:
            sources, total = SourceService.get_sources(
                db=db,
                tenant_id=tenant_id,
                source_type=type,
                health_status=status,  # Use health_status for filtering
                site=site,
                page=page,
                size=eff_size
            )
            
            # Update statuses before returning
            SourceService.update_source_statuses(db)
            
        except OperationalError as e:
            if "no such table: sources" in str(e):
                # Table doesn't exist, create it and retry
                _ensure_sources_table()
                
                # Retry the query
                sources, total = SourceService.get_sources(
                    db=db,
                    tenant_id=tenant_id,
                    source_type=type,
                    health_status=status,
                    site=site,
                    page=page,
                    size=eff_size
                )
                
                # Update statuses before returning
                SourceService.update_source_statuses(db)
            else:
                # Re-raise if it's a different database error
                raise
        
        pages = (total + eff_size - 1) // eff_size
        
        resp = SourceListResponse(
            sources=[SourceResponse(**source.to_dict()) for source in sources],
            total=total,
            page=page,
            size=eff_size,
            pages=pages
        )
        # Fill alias fields for UI compatibility
        resp.items = resp.sources
        resp.page_size = resp.size
        return resp
    finally:
        db.close()


@router.get("/sources/{source_id}", response_model=SourceResponse, dependencies=[Depends(require_scopes("read_sources"))])
async def get_source(
    source_id: str,
    request: Request
):
    """Get source details by ID"""
    tenant_id = getattr(request.state, 'tenant_id', 'default')
    
    db = SessionLocal()
    try:
        source = SourceService.get_source_by_id(db, source_id, tenant_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Update status before returning
        SourceService.update_source_statuses(db)
        db.refresh(source)
        
        return SourceResponse(**source.to_dict())
    finally:
        db.close()


@router.get("/sources/{source_id}/status", response_model=SourceStatus, dependencies=[Depends(require_scopes("read_sources"))])
async def get_source_status(
    source_id: str,
    request: Request
):
    """Get source status with EPS and error percentage"""
    tenant_id = getattr(request.state, 'tenant_id', 'default')
    
    db = SessionLocal()
    try:
        source = SourceService.get_source_by_id(db, source_id, tenant_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Get metrics from the metrics module
        from ..metrics import get_source_eps_1m, get_source_error_pct_1m
        
        eps_1m = get_source_eps_1m(source_id)
        error_pct_1m = get_source_error_pct_1m(source_id)
        
        return SourceStatus(
            last_seen_ts=source.last_seen_ts,
            eps_1m=eps_1m,
            error_pct_1m=error_pct_1m
        )
    finally:
        db.close()


@router.get("/sources/{source_id}/metrics", response_model=SourceMetrics, dependencies=[Depends(require_scopes("read_sources"))])
async def get_source_metrics(
    source_id: str,
    request: Request,
    window: int = Query(900, ge=60, le=3600, description="Metrics window in seconds")
):
    """Get source metrics"""
    tenant_id = getattr(request.state, 'tenant_id', 'default')
    
    db = SessionLocal()
    try:
        source = SourceService.get_source_by_id(db, source_id, tenant_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        metrics = SourceService.get_source_metrics(source.collector, source.last_seen)
        return metrics
    finally:
        db.close()


@router.post("/sources/{source_id}/admission/test")
async def test_admission(
    source_id: str,
    request: Request
):
    """Test admission control for a specific source and client IP"""
    # Check if user has admin scope or owns the source
    scopes = getattr(request.state, 'scopes', [])
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    if "admin" not in scopes:
        # Non-admin users can only test their own sources
        db = SessionLocal()
        try:
            source = SourceService.get_source_by_id(db, source_id, tenant_id)
            if not source:
                raise HTTPException(status_code=404, detail="Source not found")
        finally:
            db.close()
    else:
        # Admin can test any source
        db = SessionLocal()
        try:
            source = SourceService.get_source_by_id_admin(db, source_id)
            if not source:
                raise HTTPException(status_code=404, detail="Source not found")
        finally:
            db.close()
    
    try:
        body = await request.json()
        client_ip = body.get("client_ip")
        
        if not client_ip:
            raise HTTPException(status_code=400, detail="client_ip is required")
        
        # Test admission using the same logic as B1
        from ..security import validate_source_admission
        allowed, reason = validate_source_admission(source, client_ip)
        
        return {
            "allowed": allowed,
            "reason": reason,
            "source_id": source_id,
            "client_ip": client_ip,
            "source_status": source.status,
            "source_allowed_ips": source.allowed_ips
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

@router.patch("/sources/{source_id}")
async def update_source(
    source_id: str,
    source_data: dict,
    request: Request
):
    """Update a source"""
    # Check if user has admin scope or owns the source
    scopes = getattr(request.state, 'scopes', [])
    tenant_id = getattr(request.state, 'tenant_id', 'default')
    
    db = SessionLocal()
    try:
        if "admin" not in scopes:
            # Non-admin users can only update their own sources
            source = SourceService.get_source_by_id(db, source_id, tenant_id)
            if not source:
                raise HTTPException(status_code=404, detail="Source not found")
        else:
            # Admin can update any source
            source = SourceService.get_source_by_id_admin(db, source_id)
            if not source:
                raise HTTPException(status_code=404, detail="Source not found")
        
        # Validate the update data
        from ..services.validation import validate_source_limits
        is_valid, error = validate_source_limits(source_data)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error)
        
        # Update the source
        updated_source = SourceService.update_source(db, source_id, source_data)
        return SourceResponse(**updated_source.to_dict())
        
    finally:
        db.close()

@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: str,
    request: Request
):
    """Delete a source"""
    # Check if user has admin scope or owns the source
    scopes = getattr(request.state, 'scopes', [])
    tenant_id = getattr(request.state, 'tenant_id', 'default')
    
    db = SessionLocal()
    try:
        if "admin" not in scopes:
            # Non-admin users can only delete their own sources
            source = SourceService.get_source_by_id(db, source_id, tenant_id)
            if not source:
                raise HTTPException(status_code=404, detail="Source not found")
        else:
            # Admin can delete any source
            source = SourceService.get_source_by_id_admin(db, source_id)
            if not source:
                raise HTTPException(status_code=404, detail="Source not found")
        
        # Delete the source
        SourceService.delete_source(db, source_id)
        return {"message": "Source deleted successfully"}
        
    finally:
        db.close()
