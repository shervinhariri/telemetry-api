from fastapi import APIRouter, Query, UploadFile, File, HTTPException
from fastapi.responses import Response
from typing import Optional
import os
from pathlib import Path
from datetime import datetime

router = APIRouter()

def get_log_file_path() -> Path:
    """Get the path to the application log file"""
    return Path("/data/logs/app.log")

@router.get("/logs")
def get_logs(limit: int = Query(100, ge=1, le=1000), 
             max_bytes: int = Query(2000000, ge=1024, le=5000000),
             format: str = Query("text", regex="^(text|json)$")):
    """Get logs with limit parameter for compatibility"""
    return tail_logs(max_bytes=max_bytes, format=format)

@router.get("/logs/tail")
def tail_logs(max_bytes: int = Query(2000000, ge=1024, le=5000000), 
              format: str = Query("text", regex="^(text|json)$")):
    """Get the tail of the application log file"""
    log_file = get_log_file_path()
    
    if not log_file.exists():
        if format == "json":
            return {"lines": [], "error": "Log file not found"}
        return "Log file not found"
    
    try:
        # Read the last N bytes
        with open(log_file, "rb") as f:
            f.seek(0, 2)  # Seek to end
            file_size = f.tell()
            start_pos = max(0, file_size - max_bytes)
            f.seek(start_pos)
            content = f.read().decode("utf-8", errors="replace")
        
        # Split into lines and get the last few complete lines
        lines = content.split("\n")
        if len(lines) > 1:
            lines = lines[1:]  # Remove partial first line
        
        if format == "json":
            return {"lines": lines, "total_bytes": len(content)}
        else:
            return Response(content="\n".join(lines), media_type="text/plain")
            
    except Exception as e:
        if format == "json":
            return {"lines": [], "error": str(e)}
        return f"Error reading log file: {str(e)}"

@router.get("/logs/download")
def download_logs(max_bytes: int = Query(2000000, ge=1024, le=5000000)):
    """Download the tail of the application log file"""
    log_file = get_log_file_path()
    
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    
    try:
        # Read the last N bytes
        with open(log_file, "rb") as f:
            f.seek(0, 2)  # Seek to end
            file_size = f.tell()
            start_pos = max(0, file_size - max_bytes)
            f.seek(start_pos)
            content = f.read()
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"app_log_tail_{timestamp}.log"
        
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading log file: {str(e)}")

@router.post("/logs/upload")
async def upload_log_file(file: UploadFile = File(...)):
    """Upload a log file for support review"""
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Create uploads directory
    uploads_dir = Path("/data/uploads")
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
    uploads_dir = Path("/data/uploads")
    
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
