"""
Request audit API endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Request, Response, Header
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
import json
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict

from ..audit import mask_api_key, get_active_clients_count

router = APIRouter()

from ..observability.audit import list_audits
from ..audit import mask_api_key, get_active_clients_count

def get_audit_summary(window_minutes: int = 15) -> Dict[str, Any]:
    """Get audit summary for dashboard cards"""
    # Get recent audits from the new audit system
    recent_audits = list_audits(limit=1000, exclude_monitoring=True)  # Get all recent audits
    
    # Filter by time window
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=window_minutes)
    
    recent_requests = [
        req for req in recent_audits 
        if datetime.fromisoformat(req.get('ts', now.isoformat())) >= cutoff
    ]
    
    # Calculate metrics
    total_requests = len(recent_requests)
    
    # Status code breakdown
    status_codes = defaultdict(int)
    for req in recent_requests:
        status = req.get('status', 200)
        if 200 <= status < 300:
            status_codes['2xx'] += 1
        elif 400 <= status < 500:
            status_codes['4xx'] += 1
        elif 500 <= status < 600:
            status_codes['5xx'] += 1
    
    # P95 latency
    latencies = [req.get('latency_ms', 0) for req in recent_requests]
    p95_latency = 0
    if latencies:
        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_index]
    
    # Active clients
    active_clients = get_active_clients_count()
    
    return {
        "requests": total_requests,
        "codes": dict(status_codes),
        "p95_latency_ms": p95_latency,
        "active_clients": active_clients
    }

@router.get("/admin/requests/summary")
async def get_requests_summary(
    Authorization: Optional[str] = Header(None),
    window: int = Query(15, description="Time window in minutes")
):
    """Get requests summary for dashboard cards"""
    from ..auth import require_api_key
    
    # Require admin scope
    require_api_key(Authorization, required_scopes=["admin", "read_requests"])
    
    return get_audit_summary(window)

@router.get("/admin/requests")
async def get_requests(
    response: Response,
    Authorization: Optional[str] = Header(None),
    limit: int = Query(50, ge=1, le=200, description="Number of requests to return"),
    exclude_monitoring: bool = Query(True, description="Exclude monitoring endpoints"),
    status: str = Query("any", pattern="^(any|2xx|4xx|5xx)$", description="Status filter"),
    path: Optional[str] = Query(None, description="Path filter"),
    if_none_match: Optional[str] = Query(None, description="ETag for caching")
):
    """Get recent request audits with timeline events and ETag support"""
    from hashlib import sha1
    from ..auth import require_api_key
    
    # Require admin scope
    require_api_key(Authorization, required_scopes=["admin", "read_requests"])
    
    # Get recent audits with filtering
    items = list_audits(
        limit=limit,
        exclude_monitoring=exclude_monitoring,
        status_filter=status,
        path_filter=path
    )
    
    # Generate ETag for caching
    signature = sha1(f"{len(items)}|{items[-1]['id'] if items else 'none'}".encode()).hexdigest()
    etag = f'W/"{signature}"'
    
    # Return 304 if unchanged
    if if_none_match and if_none_match == etag:
        response.status_code = 304
        return
    
    response.headers["ETag"] = etag
    
    return {
        "items": items,
        "total": len(items)
    }

@router.get("/admin/requests/stream")
async def stream_requests(
    request: Request,
    since: Optional[str] = Query(None, description="Start time (ISO format)"),
    method: Optional[str] = Query(None, description="HTTP method"),
    status: Optional[int] = Query(None, description="HTTP status code"),
    endpoint: Optional[str] = Query(None, description="API endpoint path"),
    client_ip: Optional[str] = Query(None, description="Client IP address")
):
    """Stream audit records via Server-Sent Events"""
    
    async def generate():
        """Generate SSE events"""
        try:
            # Send initial connection message
            yield f"id: {datetime.utcnow().isoformat()}\n"
            yield "event: connected\n"
            yield f"data: {json.dumps({'message': 'Connected to audit stream'})}\n\n"
            
            # Mock streaming - replace with real-time database queries
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                # Get recent audit records
                recent_data = in_memory_audit_logs[-10:]  # Last 10 records
                
                for record in recent_data:
                    # Apply filters
                    if since:
                        since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                        if record.get('ts', datetime.utcnow()) < since_dt:
                            continue
                    
                    if method and record.get('method') != method.upper():
                        continue
                    
                    if status and record.get('status') != status:
                        continue
                    
                    if endpoint and endpoint not in record.get('path', ''):
                        continue
                    
                    if client_ip and client_ip not in record.get('client_ip', ''):
                        continue
                    
                    # Mask API key
                    if 'api_key' in record:
                        record['api_key_masked'] = mask_api_key(record['api_key'])
                        del record['api_key']
                    
                    # Convert datetime objects to ISO strings for JSON serialization
                    serializable_record = {}
                    for key, value in record.items():
                        if isinstance(value, datetime):
                            serializable_record[key] = value.isoformat()
                        else:
                            serializable_record[key] = value
                    
                    # Send SSE event
                    yield f"id: {serializable_record.get('trace_id', 'unknown')}\n"
                    yield "event: request\n"
                    yield f"data: {json.dumps(serializable_record)}\n\n"
                
                # Wait before next poll
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            # Client disconnected
            pass
        except Exception as e:
            # Send error event
            yield f"id: {datetime.utcnow().isoformat()}\n"
            yield "event: error\n"
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@router.get("/admin/requests/{request_id}")
async def get_request_detail(request_id: int):
    """Get detailed information about a specific request"""
    # Find the request by ID
    for req in in_memory_audit_logs:
        if req.get('id') == request_id:
            return req
    
    raise HTTPException(status_code=404, detail="Request not found")

@router.get("/api/requests")
async def get_requests_api(
    limit: int = Query(50, ge=1, le=1000, description="Number of requests to return"),
    status_filter: Optional[str] = Query(None, description="Status filter (2xx, 4xx, 5xx)")
):
    """Enhanced API endpoint for requests with timeline events"""
    # Get recent audits with filtering
    audits = list_audits(
        limit=limit,
        exclude_monitoring=True,
        status_filter=status_filter or "any"
    )
    
    # Calculate aggregations for state boxes
    total_requests = len(audits)
    succeeded = sum(1 for req in audits if 200 <= req.get('status', 0) < 300)
    failed = sum(1 for req in audits if req.get('status', 0) >= 400)
    
    # Calculate average latency
    latencies = [req.get('latency_ms', 0) for req in audits if req.get('latency_ms', 0) > 0]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    # Prepare response data with enhanced fields for UI
    items = []
    for req in audits:
        item = req.copy()
        
        # Add computed fields for UI
        item['records'] = item.get('summary', {}).get('records', 0)
        item['risk_avg'] = item.get('summary', {}).get('risk_avg', 0)
        item['latency_ms'] = item.get('latency_ms', 0)
        
        # Extract source IP for display
        item['source_ip'] = item.get('client_ip', 'unknown')
        
        items.append(item)
    
    return {
        "items": items,
        "total": total_requests,
        "succeeded": succeeded,
        "failed": failed,
        "avg_latency_ms": round(avg_latency, 2)
    }
