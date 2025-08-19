from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class SourceCreate(BaseModel):
    id: str = Field(..., description="Unique source identifier")
    tenant_id: str = Field(..., description="Tenant ID")
    type: str = Field(..., description="Source type (cisco_asa, cisco_ftd, palo_alto, aws_vpc, etc.)")
    display_name: str = Field(..., description="Human-readable display name")
    collector: str = Field(..., description="Collector ID (e.g. gw-local)")
    site: Optional[str] = Field(None, description="Site location (Krakow, HQ, etc.)")
    tags: Optional[str] = Field(None, description="JSON array string of tags")
    notes: Optional[str] = Field(None, description="Additional notes")


class SourceUpdate(BaseModel):
    display_name: Optional[str] = Field(None, description="Human-readable display name")
    site: Optional[str] = Field(None, description="Site location")
    tags: Optional[str] = Field(None, description="JSON array string of tags")
    notes: Optional[str] = Field(None, description="Additional notes")


class SourceResponse(BaseModel):
    id: str
    tenant_id: str
    type: str
    display_name: str
    collector: str
    site: Optional[str]
    tags: Optional[str]
    status: str
    last_seen: Optional[str]
    notes: Optional[str]


class SourceMetrics(BaseModel):
    eps_1m: float = Field(0.0, description="Events per second (1 minute average)")
    records_24h: int = Field(0, description="Total records in last 24 hours")
    error_pct_15m: float = Field(0.0, description="Error percentage in last 15 minutes")
    avg_risk_15m: float = Field(0.0, description="Average risk score in last 15 minutes")
    last_seen: Optional[str] = Field(None, description="Last seen timestamp")


class SourceListResponse(BaseModel):
    sources: List[SourceResponse]
    total: int
    page: int
    size: int
    pages: int
