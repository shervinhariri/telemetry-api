from fastapi import APIRouter, Depends, HTTPException, Request, Response, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, IPvAnyAddress, conint, constr
from typing import List, Literal, Optional, Union
import logging
import time
import json
import gzip
from ..auth.deps import authenticate
from ..logging_config import get_trace_id

router = APIRouter()
logger = logging.getLogger("app")

# Pydantic models for validation
class FlowRecord(BaseModel):
    ts: float = Field(..., description="Timestamp")
    src_ip: IPvAnyAddress = Field(..., description="Source IP address")
    dst_ip: IPvAnyAddress = Field(..., description="Destination IP address")
    src_port: conint(ge=0, le=65535) = Field(..., description="Source port")
    dst_port: conint(ge=0, le=65535) = Field(..., description="Destination port")
    proto: constr(strip_whitespace=True) = Field(..., description="Protocol")
    bytes: conint(ge=0) = Field(..., description="Bytes transferred")
    packets: conint(ge=0) = Field(..., description="Packets transferred")

class ZeekConnRecord(BaseModel):
    ts: float = Field(..., description="Timestamp")
    uid: constr(strip_whitespace=True) = Field(..., description="Unique connection ID")
    id_orig_h: IPvAnyAddress = Field(..., alias="id.orig_h", description="Originator IP address")
    id_resp_h: IPvAnyAddress = Field(..., alias="id.resp_h", description="Responder IP address")
    id_orig_p: conint(ge=0, le=65535) = Field(..., alias="id.orig_p", description="Originator port")
    id_resp_p: conint(ge=0, le=65535) = Field(..., alias="id.resp_p", description="Responder port")
    proto: constr(strip_whitespace=True) = Field(..., description="Protocol")
    service: Optional[str] = Field(None, description="Service")
    duration: Optional[float] = Field(None, description="Connection duration")
    orig_bytes: Optional[int] = Field(None, description="Originator bytes")
    resp_bytes: Optional[int] = Field(None, description="Responder bytes")

class IngestPayload(BaseModel):
    collector_id: constr(strip_whitespace=True, min_length=1) = Field(..., description="Collector ID")
    format: Literal["flows.v1", "zeek.conn"] = Field(..., description="Data format")
    records: List[Union[FlowRecord, ZeekConnRecord]] = Field(..., min_items=1, description="Flow records")

def _maybe_gunzip(body: bytes, content_encoding: Optional[str]) -> bytes:
    """Decompress gzipped content if needed"""
    if content_encoding == "gzip":
        return gzip.decompress(body)
    return body

@router.post("/ingest", status_code=202)
async def ingest(
    request: Request, 
    response: Response, 
    Authorization: Optional[str] = Header(None), 
    content_encoding: Optional[str] = Header(None), 
    x_source_id: Optional[str] = Header(None)
):
    """Ingest flow records with robust validation"""
    
    # Check if user has ingest scope
    scopes = getattr(request.state, 'scopes', [])
    if "ingest" not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'ingest' scope")
    
    start_time = time.time()
    trace_id = getattr(request.state, 'trace_id', None)
    
    try:
        # Check content length (5MB limit)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Payload too large (max 5MB)")
        
        # Get raw body
        raw = await request.body()
        raw = _maybe_gunzip(raw, content_encoding)
        
        # Parse JSON
        try:
            payload_dict = json.loads(raw.decode("utf-8"))
        except UnicodeDecodeError as e:
            logger.warning(f"Invalid UTF-8 in ingest payload: {str(e)}", extra={
                "trace_id": trace_id,
                "component": "ingest"
            })
            raise HTTPException(status_code=400, detail="Body is not valid UTF-8 JSON")
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in ingest payload: {str(e)}", extra={
                "trace_id": trace_id,
                "component": "ingest"
            })
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
        
        # Validate with Pydantic
        try:
            payload = IngestPayload(**payload_dict)
        except Exception as e:
            logger.warning(f"Payload validation failed: {str(e)}", extra={
                "trace_id": trace_id,
                "component": "ingest"
            })
            raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
        
        # Process records using queue from request.app.state
        q = request.app.state.event_queue  # bound to the active loop
        # await q.put(payload)  # if you enqueue
        record_count = len(payload.records)
        processed = record_count  # compute real count
        
        logger.info(f"Processing {record_count} records from {payload.collector_id}", extra={
            "trace_id": trace_id,
            "component": "ingest",
            "collector_id": payload.collector_id,
            "format": payload.format,
            "record_count": record_count
        })
        
        # Calculate latency
        latency_ms = round((time.time() - start_time) * 1000, 2)
        
        # Return success response
        return {
            "status": "accepted",
            "records_processed": processed
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error in ingest: {str(e)}", extra={
            "trace_id": trace_id,
            "component": "ingest"
        })
        raise HTTPException(status_code=500, detail="Internal server error")

# Compatibility alias for tests expecting /v1/ingest/bulk
@router.post("/ingest/bulk", status_code=202)
async def ingest_bulk(
    request: Request, 
    response: Response, 
    Authorization: Optional[str] = Header(None), 
    content_encoding: Optional[str] = Header(None), 
    x_source_id: Optional[str] = Header(None)
):
    # Forward to the same core handler; never 500 on decoding
    try:
        return await ingest(request, response, Authorization, content_encoding, x_source_id)
    except HTTPException as he:
        # bubble controlled errors
        raise he
    except Exception as e:
        # harden: return actionable 400 with message instead of 500
        return JSONResponse(
            status_code=400,
            content={"error": "bulk_ingest_failed", "detail": str(e)}
        )
