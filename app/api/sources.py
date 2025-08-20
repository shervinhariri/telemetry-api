from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from app.db import SessionLocal

from app.schemas.source import (
    SourceCreate, SourceResponse, SourceListResponse, SourceMetrics
)
from app.services.sources import SourceService
from app.models.source import Source

router = APIRouter()


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


@router.get("/sources", response_model=SourceListResponse)
async def list_sources(
    request: Request,
    tenant: Optional[str] = Query(None, description="Filter by tenant"),
    type: Optional[str] = Query(None, description="Filter by source type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    site: Optional[str] = Query(None, description="Filter by site"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size")
):
    """Get paginated list of sources"""
    # Check if user has read_metrics scope
    scopes = getattr(request.state, 'scopes', [])
    if "read_metrics" not in scopes:
        raise HTTPException(status_code=403, detail="read_metrics scope required")
    
    # Use tenant from auth if not specified
    tenant_id = tenant or getattr(request.state, 'tenant_id', 'default')
    
    db = SessionLocal()
    try:
        sources, total = SourceService.get_sources(
            db=db,
            tenant_id=tenant_id,
            source_type=type,
            health_status=status,  # Use health_status for filtering
            site=site,
            page=page,
            size=size
        )
        
        # Update statuses before returning
        SourceService.update_source_statuses(db)
        
        pages = (total + size - 1) // size
        
        return SourceListResponse(
            sources=[SourceResponse(**source.to_dict()) for source in sources],
            total=total,
            page=page,
            size=size,
            pages=pages
        )
    finally:
        db.close()


@router.get("/sources/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: str,
    request: Request
):
    """Get source details by ID"""
    # Check if user has read_metrics scope
    scopes = getattr(request.state, 'scopes', [])
    tenant_id = getattr(request.state, 'tenant_id', 'default')
    
    if "read_metrics" not in scopes:
        raise HTTPException(status_code=403, detail="read_metrics scope required")
    
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


@router.get("/sources/{source_id}/metrics", response_model=SourceMetrics)
async def get_source_metrics(
    source_id: str,
    request: Request,
    window: int = Query(900, ge=60, le=3600, description="Metrics window in seconds")
):
    """Get source metrics"""
    # Check if user has read_metrics scope
    scopes = getattr(request.state, 'scopes', [])
    tenant_id = getattr(request.state, 'tenant_id', 'default')
    
    if "read_metrics" not in scopes:
        raise HTTPException(status_code=403, detail="read_metrics scope required")
    
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

@router.put("/sources/{source_id}")
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
