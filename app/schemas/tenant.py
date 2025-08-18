from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class TenantCreate(BaseModel):
    tenant_id: str = Field(..., max_length=64)
    name: str
    retention_days: int = 7
    quotas: Dict[str, int] = {"eps": 600, "batch_max": 10000, "dlq_max": 100000}
    redaction: Dict[str, List[str]] = {"fields": []}

class TenantOut(TenantCreate):
    created_at: Optional[str]
