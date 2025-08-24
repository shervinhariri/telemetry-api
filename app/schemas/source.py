from typing import Optional, List, Union
from pydantic import BaseModel, Field
from datetime import datetime


class SourceCreate(BaseModel):
    id: str = Field(..., description="Unique source identifier")
    tenant_id: str = Field(..., description="Tenant ID")
    type: str = Field(..., description="Source type (udp, http) - declared intent")
    display_name: str = Field(..., description="Human-readable display name")
    collector: str = Field(..., description="Collector ID (e.g. gw-local)")
    site: Optional[str] = Field(None, description="Site location (Krakow, HQ, etc.)")
    tags: Optional[str] = Field(None, description="JSON array string of tags")
    notes: Optional[str] = Field(None, description="Additional notes")
    # Security fields
    status: Optional[str] = Field("enabled", description="Source status: enabled or disabled")
    allowed_ips: Optional[str] = Field("[]", description="JSON array of allowed CIDR strings")
    max_eps: Optional[int] = Field(0, description="Maximum events per second (0 = unlimited)")
    block_on_exceed: Optional[bool] = Field(True, description="Block traffic when EPS limit exceeded")
    # New fields
    enabled: Optional[bool] = Field(True, description="Source enabled status")
    eps_cap: Optional[int] = Field(0, description="EPS cap (0 = unlimited)")


class SourceUpdate(BaseModel):
    display_name: Optional[str] = Field(None, description="Human-readable display name")
    site: Optional[str] = Field(None, description="Site location")
    tags: Optional[str] = Field(None, description="JSON array string of tags")
    notes: Optional[str] = Field(None, description="Additional notes")
    # Security fields
    status: Optional[str] = Field(None, description="Source status: enabled or disabled")
    allowed_ips: Optional[str] = Field(None, description="JSON array of allowed CIDR strings")
    max_eps: Optional[int] = Field(None, description="Maximum events per second (0 = unlimited)")
    block_on_exceed: Optional[bool] = Field(None, description="Block traffic when EPS limit exceeded")
    # New fields
    enabled: Optional[bool] = Field(None, description="Source enabled status")
    eps_cap: Optional[int] = Field(None, description="EPS cap (0 = unlimited)")


class SourceResponse(BaseModel):
    id: str
    tenant_id: str
    type: str
    origin: Optional[str] = Field(None, description="Actual traffic origin (udp, http, unknown)")
    display_name: str
    collector: str
    site: Optional[str]
    tags: Optional[str]
    health_status: str
    last_seen: Optional[str]
    notes: Optional[str]
    # Security fields
    status: str
    allowed_ips: str
    max_eps: int
    block_on_exceed: bool
    # New fields
    enabled: bool
    eps_cap: int
    last_seen_ts: Optional[int]
    eps_1m: Optional[float]
    error_pct_1m: Optional[float]
    created_at: int
    updated_at: int


class SourceMetrics(BaseModel):
    eps_1m: float = Field(0.0, description="Events per second (1 minute average)")
    records_24h: int = Field(0, description="Total records in last 24 hours")
    error_pct_15m: float = Field(0.0, description="Error percentage in last 15 minutes")
    avg_risk_15m: float = Field(0.0, description="Average risk score in last 15 minutes")
    last_seen: Optional[str] = Field(None, description="Last seen timestamp")


class SourceStatus(BaseModel):
    last_seen_ts: Optional[int] = Field(None, description="Last seen timestamp")
    eps_1m: Optional[float] = Field(0.0, description="Events per second (1 minute average)")
    error_pct_1m: Optional[float] = Field(0.0, description="Error percentage (1 minute average)")


class SourceListResponse(BaseModel):
    # Existing fields
    sources: List[SourceResponse]
    total: int
    page: int
    size: int
    pages: int
    # New alias fields for UI/contract compatibility
    items: Optional[List[SourceResponse]] = None
    page_size: Optional[int] = None
