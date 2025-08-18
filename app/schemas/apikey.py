from pydantic import BaseModel, Field
from typing import List, Optional

class ApiKeyCreate(BaseModel):
    tenant_id: str = Field(..., max_length=64)
    scopes: List[str] = ["ingest"]

class ApiKeyOut(BaseModel):
    key_id: str
    tenant_id: str
    scopes: List[str]
    disabled: bool
    created_at: Optional[str]
