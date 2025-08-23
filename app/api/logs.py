from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from typing import Optional, List, AsyncGenerator
import json
import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from ..auth.deps import authenticate
from ..logging_config import memory_handler, get_trace_id

router = APIRouter()

@router.get("/logs")
async def get_logs(
    since: Optional[str] = Query(None, description="RFC3339 timestamp to filter logs from"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of logs to return"),
    level: Optional[str] = Query(None, description="Filter by log level (INFO, WARNING, ERROR, etc.)"),
    trace_id: Optional[str] = Query(None, description="Filter by trace ID"),
    endpoint: Optional[str] = Query(None, description="Filter by endpoint path"),
    current_user: dict = Depends(authenticate)
):
    """Get logs from memory buffer with optional filtering"""
    
    # Get logs from memory handler
    logs = memory_handler.get_logs(since=since, limit=limit)
    
    # Apply filters
    if level:
        logs = [log for log in logs if log.get("level") == level.upper()]
    
    if trace_id:
        logs = [log for log in logs if log.get("trace_id") == trace_id]
    
    if endpoint:
        logs = [log for log in logs if log.get("path") and endpoint in log.get("path")]
    
    return {
        "logs": logs,
        "count": len(logs),
        "since": since,
        "limit": limit,
        "filters": {
            "level": level,
            "trace_id": trace_id,
            "endpoint": endpoint
        }
    }

@router.get("/logs/stream")
async def stream_logs(
    request: Request,
    current_user: Optional[dict] = Depends(authenticate)
):
    """
    Stream logs as Server-Sent Events (SSE)
    - Accepts Authorization header (if your global auth middleware adds it), OR
    - Accepts ?key= for EventSource which cannot set custom headers.
    """
    # If normal auth didn't work, try query key fallback for EventSource
    if not current_user:
        query_key = request.query_params.get("key")
        if not query_key:
            raise HTTPException(status_code=401, detail="Missing API key")
        # For now, just validate that a key is present
        # In production, you'd validate against your auth system
    
    async def log_stream():
        """Stream logs as SSE"""
        last_count = 0
        
        while True:
            try:
                # Get current logs
                logs = memory_handler.get_logs()
                current_count = len(logs)
                
                # Send new logs since last check
                if current_count > last_count:
                    new_logs = logs[last_count:]
                    for log in new_logs:
                        yield f"data: {json.dumps(log)}\n\n"
                    
                    last_count = current_count
                
                # Keep connection alive
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                error_log = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": "ERROR",
                    "logger": "logs.stream",
                    "msg": f"Log stream error: {str(e)}",
                    "trace_id": get_trace_id(),
                    "component": "api"
                }
                yield f"data: {json.dumps(error_log)}\n\n"
                break
    
    return StreamingResponse(
        log_stream(),
        media_type="text/event-stream",  # ✅ correct for SSE
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/logs/tail")
async def logs_tail(
    max_bytes: int = Query(50000, ge=1000, le=1000000, description="Maximum bytes to return"),
    format: str = Query("text", description="Output format: text or json"),
    current_user: dict = Depends(authenticate)
):
    """Compatibility endpoint for legacy UI - returns recent logs in text or JSON format"""
    
    # Get logs from memory handler
    logs = memory_handler.get_logs(limit=1000)  # Get recent logs
    
    if format.lower() == "json":
        # Return JSON format with lines array
        lines = []
        for log in logs:
            # Format as text line for compatibility
            timestamp = log.get("timestamp", "")
            level = log.get("level", "INFO")
            msg = log.get("msg", "")
            trace_id = log.get("trace_id", "")
            
            line = f"{timestamp} [{level}] {msg}"
            if trace_id:
                line += f" (trace_id: {trace_id})"
            lines.append(line)
        
        return {"lines": lines}
    else:
        # Return text format
        lines = []
        for log in logs:
            timestamp = log.get("timestamp", "")
            level = log.get("level", "INFO")
            msg = log.get("msg", "")
            trace_id = log.get("trace_id", "")
            
            line = f"{timestamp} [{level}] {msg}"
            if trace_id:
                line += f" (trace_id: {trace_id})"
            lines.append(line)
        
        # Join lines and truncate to max_bytes
        content = "\n".join(lines)
        if len(content.encode('utf-8')) > max_bytes:
            # Truncate to approximately max_bytes
            truncated = content.encode('utf-8')[:max_bytes].decode('utf-8', errors='ignore')
            # Try to end at a newline
            last_newline = truncated.rfind('\n')
            if last_newline > max_bytes // 2:  # Only if we can find a reasonable break point
                truncated = truncated[:last_newline]
            content = truncated
        
        return content

@router.get("/logs/download")
async def download_logs(
    since: Optional[str] = Query(None, description="RFC3339 timestamp to filter logs from"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of logs to return"),
    current_user: dict = Depends(authenticate)
):
    """Download logs as JSON lines file"""
    
    logs = memory_handler.get_logs(since=since, limit=limit)
    
    # Convert to JSON lines format
    json_lines = "\n".join(json.dumps(log) for log in logs)
    
    # Generate filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"telemetry-logs-{timestamp}.jsonl"
    
    return StreamingResponse(
        iter([json_lines]),
        media_type="application/jsonl",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(json_lines))
        }
    )
