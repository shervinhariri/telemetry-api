from pydantic import BaseModel, Field
from typing import Dict, Any

class OutputConfigCreate(BaseModel):
    tenant_id: str = Field(..., max_length=64)
    type: str = Field(..., pattern="^(splunk|elastic)$")
    config: Dict[str, Any] = {}
    enabled: bool = False

class OutputConfigOut(BaseModel):
    id: int
    tenant_id: str
    type: str
    config: Dict[str, Any]
    enabled: bool
