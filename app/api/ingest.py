from fastapi import APIRouter, Depends, HTTPException, Request, Response, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, IPvAnyAddress, conint, constr
from typing import List, Literal, Optional, Union, Dict, Any
import logging
import time
import json
import gzip
import io
from ..auth.deps import authenticate
from ..logging_config import get_trace_id
from ..services.prometheus_metrics import prometheus_metrics
from ..queue_manager import queue_manager
from ..config import QUEUE_RETRY_AFTER_SECONDS
from .response_builders import (
    build_size_limit_response, build_count_limit_response, build_shape_error_response,
    build_backpressure_response, build_validation_error_response, build_json_error_response
)

router = APIRouter()
logger = logging.getLogger("app")

# Ingest limits
MAX_COMPRESSED_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_RECORDS_PER_BATCH = 10000

def _maybe_gunzip(body: bytes, content_encoding: Optional[str]) -> bytes:
    """Decompress gzipped content if needed"""
    if content_encoding == "gzip":
        return gzip.decompress(body)
    return body

def _detect_batch_format(content: str) -> tuple[str, int]:
    """
    Detect if content is JSON array or JSONL and count records.
    Returns (format_type, record_count)
    """
    content = content.strip()
    if not content:
        return "empty", 0
    
    # Check if it's a JSON array
    if content.startswith('['):
        try:
            # Parse as JSON array and count elements
            data = json.loads(content)
            if isinstance(data, list):
                return "json", len(data)
            else:
                return "invalid", 0
        except json.JSONDecodeError:
            return "invalid", 0
    
    # Check if it's JSONL (newline-delimited JSON)
    lines = content.split('\n')
    record_count = 0
    for line in lines:
        line = line.strip()
        if line:  # Skip blank lines
            if line.startswith('{'):
                record_count += 1
            else:
                return "invalid", 0
    
    return "jsonl", record_count

def _validate_batch_shape(content: str) -> tuple[bool, str]:
    """
    Pre-screen batch shape before deep parsing.
    Returns (is_valid, format_type)
    """
    content = content.strip()
    if not content:
        return False, "empty"
    
    # Check for JSON array
    if content.startswith('['):
        return True, "json"
    
    # Check for JSON object (for compatibility with object wrapper format)
    if content.startswith('{'):
        return True, "json"
    
    # Check for JSONL (contains newlines and starts with {)
    if '\n' in content and content.lstrip().startswith('{'):
        return True, "jsonl"
    
    return False, "invalid"

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
    format: Literal["flows.v1", "zeek.conn", "zeek"] = Field(..., description="Data format")
    records: List[Union[FlowRecord, ZeekConnRecord]] = Field(..., min_items=1, description="Flow records")

@router.post("/ingest", status_code=202)
async def ingest(
    request: Request, 
    response: Response, 
    Authorization: Optional[str] = Header(None), 
    content_encoding: Optional[str] = Header(None), 
    x_source_id: Optional[str] = Header(None)
):
    """Ingest flow records with robust validation and limits"""
    
    # Check if user has ingest scope
    scopes = getattr(request.state, 'scopes', [])
    if "ingest" not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions - requires 'ingest' scope")
    
    start_time = time.time()
    trace_id = getattr(request.state, 'trace_id', None)
    
    # Increment ingest batches counter
    prometheus_metrics.increment_ingest_batches(1)
    
    try:
        # Step 1: Compressed size guard (5 MB)
        raw = await request.body()
        actual_bytes = len(raw)
        
        if actual_bytes > MAX_COMPRESSED_SIZE_BYTES:
            # Log structured reject
            logger.warning("Ingest batch rejected - size limit exceeded", extra={
                "trace_id": trace_id,
                "component": "ingest",
                "event": "reject",
                "reason": "size",
                "actual_bytes": actual_bytes,
                "encoding": content_encoding or "identity"
            })
            
            # Increment reject metric
            prometheus_metrics.increment_ingest_reject("size", 1)
            
            # Return 413 with structured error
            return build_size_limit_response(content_encoding or "identity", actual_bytes)
        
        # Decompress if needed
        try:
            if content_encoding == "gzip":
                decompressed = gzip.decompress(raw)
            else:
                decompressed = raw
        except Exception as e:
            logger.warning("Failed to decompress gzipped content", extra={
                "trace_id": trace_id,
                "component": "ingest",
                "event": "reject",
                "reason": "decompress_error",
                "error": str(e)
            })
            prometheus_metrics.increment_ingest_reject("decompress_error", 1)
            return JSONResponse(
                status_code=400,
                content={"error": "decompress_failed", "detail": str(e)}
            )
        
        # Decode to string
        try:
            content = decompressed.decode("utf-8")
        except UnicodeDecodeError as e:
            logger.warning("Invalid UTF-8 in ingest payload", extra={
                "trace_id": trace_id,
                "component": "ingest",
                "event": "reject",
                "reason": "encoding_error",
                "error": str(e)
            })
            prometheus_metrics.increment_ingest_reject("encoding_error", 1)
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_encoding", "detail": "Body is not valid UTF-8"}
            )
        
        # Step 2: Batch shape pre-screen
        is_valid_shape, format_type = _validate_batch_shape(content)
        if not is_valid_shape:
            logger.warning("Ingest batch rejected - invalid shape", extra={
                "trace_id": trace_id,
                "component": "ingest",
                "event": "reject",
                "reason": "shape"
            })
            prometheus_metrics.increment_ingest_reject("shape", 1)
            return build_shape_error_response()
        
        # Step 3: Record count guard (10,000)
        format_detected, record_count = _detect_batch_format(content)
        if format_detected == "invalid":
            logger.warning("Ingest batch rejected - invalid format", extra={
                "trace_id": trace_id,
                "component": "ingest",
                "event": "reject",
                "reason": "format_error"
            })
            prometheus_metrics.increment_ingest_reject("format_error", 1)
            return JSONResponse(
                status_code=422,
                content={"error": "invalid_format", "detail": "Invalid JSON array or JSONL format"}
            )
        
        if record_count > MAX_RECORDS_PER_BATCH:
            logger.warning("Ingest batch rejected - too many records", extra={
                "trace_id": trace_id,
                "component": "ingest",
                "event": "reject",
                "reason": "count",
                "observed": record_count,
                "kind": format_detected
            })
            prometheus_metrics.increment_ingest_reject("count", 1)
            return build_count_limit_response(record_count)
        
        # Step 4: Parse and validate payload
        try:
            payload_dict = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in ingest payload", extra={
                "trace_id": trace_id,
                "component": "ingest",
                "event": "reject",
                "reason": "json_error",
                "error": str(e)
            })
            prometheus_metrics.increment_ingest_reject("json_error", 1)
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_json", "detail": str(e)}
            )
        
        # Handle both formats: JSON array and structured payload
        records_to_process = []
        collector_id = "default"
        format_type = "flows.v1"
        
        if isinstance(payload_dict, list):
            # JSON array format - treat as records directly
            records_to_process = payload_dict
        elif isinstance(payload_dict, dict):
            # Structured payload format
            if "records" in payload_dict:
                records_to_process = payload_dict["records"]
                collector_id = payload_dict.get("collector_id", "default")
                format_type = payload_dict.get("format", "flows.v1")
                # Handle both "type" and "format" fields for compatibility
                if "type" in payload_dict and "format" not in payload_dict:
                    format_type = payload_dict["type"]
            else:
                # Single record format
                records_to_process = [payload_dict]
        else:
            logger.warning("Invalid payload format", extra={
                "trace_id": trace_id,
                "component": "ingest",
                "event": "reject",
                "reason": "format_error"
            })
            prometheus_metrics.increment_ingest_reject("format_error", 1)
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_format", "detail": "Payload must be JSON array or object with records"}
            )
        
        # Step 5: Process records through queue manager
        enqueued_count = 0
        for record in records_to_process:
            # Convert record to dict if it's not already
            if hasattr(record, 'dict'):
                record_dict = record.dict()
            else:
                record_dict = record
            
            # Add metadata
            record_dict["collector_id"] = collector_id
            record_dict["format"] = format_type
            
            # Try to enqueue the record
            if queue_manager.enqueue_record(record_dict):
                enqueued_count += 1
            else:
                # Queue is full - backpressure
                logger.warning("Ingest batch rejected - queue backpressure", extra={
                    "trace_id": trace_id,
                    "component": "ingest",
                    "event": "reject",
                    "reason": "backpressure",
                    "queue_depth": queue_manager.get_queue_stats()["depth"],
                    "max_depth": queue_manager.get_queue_stats()["max"]
                })
                
                # Return 503 with Retry-After header
                return build_backpressure_response()
        
        # Log successful processing
        logger.info("Records enqueued for processing", extra={
            "trace_id": trace_id,
            "component": "ingest",
            "collector_id": collector_id,
            "format": format_type,
            "record_count": enqueued_count
        })
        
        # Observe metrics for successful batch
        prometheus_metrics.observe_ingest_batch_bytes(actual_bytes)
        prometheus_metrics.observe_ingest_records_per_batch(enqueued_count)
        
        # Calculate latency
        latency_ms = round((time.time() - start_time) * 1000, 2)
        
        # Return success response
        return {
            "status": "accepted",
            "records_processed": enqueued_count
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error("Unexpected error in ingest", extra={
            "trace_id": trace_id,
            "component": "ingest",
            "event": "error",
            "error": str(e)
        })
        prometheus_metrics.increment_ingest_reject("unexpected_error", 1)
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
        logger.error("Bulk ingest failed with unexpected error", extra={
            "component": "ingest",
            "event": "error",
            "error": str(e)
        })
        prometheus_metrics.increment_ingest_reject("bulk_error", 1)
        return JSONResponse(
            status_code=400,
            content={"error": "bulk_ingest_failed", "detail": str(e)}
        )
