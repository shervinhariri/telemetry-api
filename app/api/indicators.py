import hashlib, time
from pydantic import BaseModel, IPvAnyNetwork
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/v1", tags=["indicators"])

# in-memory registry is fine for tests
_INDICATORS = {}

class IndicatorIn(BaseModel):
    ip_or_cidr: IPvAnyNetwork
    category: str
    confidence: int

@router.put("/indicators")
def add_indicator(ind: IndicatorIn):
    raw = f"{ind.ip_or_cidr}|{ind.category}|{ind.confidence}|{int(time.time()*1000)}"
    ind_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
    _INDICATORS[ind_id] = ind.model_dump()
    return {"status": "added", "id": ind_id}

@router.delete("/indicators/{indicator_id}")
def delete_indicator(indicator_id: str):
    if indicator_id in _INDICATORS:
        del _INDICATORS[indicator_id]
        return {"status": "deleted", "id": indicator_id}
    raise HTTPException(status_code=404, detail="not found")
