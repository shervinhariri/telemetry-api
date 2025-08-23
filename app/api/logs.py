from fastapi import APIRouter, Query, UploadFile, File, HTTPException, Request
from fastapi.responses import Response
from starlette.responses import StreamingResponse
from typing import Optional, List, AsyncGenerator
from pathlib import Path
from datetime import datetime
import json
import os

router = APIRouter()

def _format_audit_lines(limit: int = 500) -> List[str]:
    """Build human-readable log lines from in-memory audit records."""
    try:
        from ..observability.audit import list_audits
    except Exception:
        return []

    items = list_audits(limit=limit, exclude_monitoring=False)
    lines: List[str] = []
    for it in items:
        ts = it.get("ts") or ""
        method = it.get("method") or ""
        path = it.get("path") or ""
        status = it.get("status")
        latency = it.get("latency_ms")
        client_ip = it.get("client_ip") or ""
        trace_id = it.get("id") or it.get("trace_id") or ""
        parts = [
            f"{ts}",
            method,
            path,
            f"status={status}" if status is not None else "status=?",
            f"latency_ms={latency}" if latency is not None else "latency_ms=?",
            f"ip={client_ip}" if client_ip else "",
            f"trace={trace_id}" if trace_id else "",
        ]
        line = " ".join(p for p in parts if p)
        lines.append(line)
    return lines

@router.get("/logs")
def get_logs(limit: int = Query(100, ge=1, le=1000), 
             max_bytes: int = Query(2000000, ge=1024, le=5000000),
             format: str = Query("text", regex="^(text|json)$")):
    """Get recent logs derived from in-memory request audits."""
    return tail_logs(max_bytes=max_bytes, format=format, limit=limit)

@router.get("/logs/tail")
def tail_logs(max_bytes: int = Query(2000000, ge=1024, le=5000000), 
              format: str = Query("text", regex="^(text|json)$"),
              limit: int = Query(500, ge=1, le=5000)):
    """Get the tail of recent logs from in-memory audits (no filesystem)."""
    try:
        lines = _format_audit_lines(limit=limit)
        content_bytes = ("\n".join(lines)).encode("utf-8", errors="replace")
        if len(content_bytes) > max_bytes:
            content_bytes = content_bytes[-max_bytes:]
        content = content_bytes.decode("utf-8", errors="replace")

        if format == "json":
            return {"lines": content.split("\n") if content else [], "total_bytes": len(content_bytes)}
        else:
            return Response(content=content, media_type="text/plain")
    except Exception as e:
        if format == "json":
            return {"lines": [], "error": str(e)}
        return f"Error building logs: {str(e)}"

@router.get("/logs/download")
def download_logs(max_bytes: int = Query(2000000, ge=1024, le=5000000)):
    """Download recent logs derived from in-memory audits as a text file."""
    try:
        lines = _format_audit_lines(limit=5000)
        content_bytes = ("\n".join(lines)).encode("utf-8", errors="replace")
        if len(content_bytes) > max_bytes:
            content_bytes = content_bytes[-max_bytes:]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audit_logs_{timestamp}.log"
        return Response(
            content=content_bytes,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error preparing logs: {str(e)}")

@router.post("/logs/upload")
async def upload_log_file(file: UploadFile = File(...)):
    """Upload a log file for support review"""
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Create uploads directory (fallback to local data/ if /data not writable)
    base = Path("/data")
    if not os.access(base.parent, os.W_OK):
        base = Path("data")
    uploads_dir = base / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in "._-")
    filename = f"{timestamp}_{safe_filename}"
    file_path = uploads_dir / filename
    
    try:
        # Save the file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        return {
            "status": "uploaded",
            "filename": filename,
            "original_name": file.filename,
            "size": len(content),
            "uploaded_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/logs/uploads")
def list_uploaded_files():
    """List uploaded files"""
    base = Path("/data")
    if not os.access(base.parent, os.W_OK):
        base = Path("data")
    uploads_dir = base / "uploads"
    
    if not uploads_dir.exists():
        return {"files": []}
    
    try:
        files = []
        for file_path in uploads_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return {"files": files}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

def _extract_api_key_from_query(request: Request) -> Optional[str]:
    # Allow EventSource (no headers) to pass the API key via query string: ?key=TEST_KEY
    # This is opt-in for SSE only. Make sure rate limits/logging still apply upstream.
    key = request.query_params.get("key")
    return key if key else None

def _validate_key_or_raise(key: Optional[str]) -> None:
    """
    Minimal placeholder. Replace with your existing validation path if available,
    e.g., calling your auth utility or checking DB/ENV.
    """
    # Example behavior:
    # - If no explicit validation system exists, allow any non-empty key (dev)
    # - If you store a canonical key in env (e.g., TEST_KEY), enforce equality
    canonical = os.getenv("DEV_SINGLE_API_KEY")  # optional; set in docker-compose for quick dev
    if canonical:
        if not key or key != canonical:
            raise HTTPException(status_code=401, detail="Invalid API key")
    else:
        if not key:
            raise HTTPException(status_code=401, detail="Missing API key")

async def event_generator() -> AsyncGenerator[str, None]:
    """
    Yield Server-Sent Events from your internal async queue/bus.
    Replace the dummy loop with your real producer.
    """
    import asyncio
    counter = 0
    while True:
        await asyncio.sleep(1)
        counter += 1
        yield f"data: {{\"tick\": {counter}}}\n\n"

@router.get("/logs/stream")
async def stream_logs(request: Request):
    """
    SSE endpoint:
    - Accepts Authorization header (if your global auth middleware adds it), OR
    - Accepts ?key= for EventSource which cannot set custom headers.
    """
    # If your normal auth dependency already ran, you can skip. Otherwise:
    # Try query key fallback so browsers can open SSE without headers.
    query_key = _extract_api_key_from_query(request)
    # If you have a real auth middleware, you can check something like:
    # if "authorization" in request.headers: (then trust middleware result)
    # Here we at least enforce having a key one way or another:
    _validate_key_or_raise(query_key)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",  # ✅ correct for SSE
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
