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
            status=status,
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
