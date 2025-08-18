from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class JobCreate(BaseModel):
    tenant_id: str = Field(..., max_length=64)
    type: str
    args: Dict[str, Any] = {}

class JobOut(BaseModel):
    job_id: str
    tenant_id: str
    type: str
    args: Dict[str, Any]
    status: str
    logs: str
    started_at: Optional[str]
    finished_at: Optional[str]
