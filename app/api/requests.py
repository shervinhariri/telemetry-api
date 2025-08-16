"""
Request audit API endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
import json
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict

from ..audit import mask_api_key, get_active_clients_count

router = APIRouter()

from ..audit import in_memory_audit_logs, mask_api_key, get_active_clients_count

def get_audit_summary(window_minutes: int = 15) -> Dict[str, Any]:
    """Get audit summary for dashboard cards"""
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=window_minutes)
    
    # Use real audit data from memory
    recent_requests = [
        req for req in in_memory_audit_logs 
        if req.get('ts', now) >= cutoff
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
    latencies = [req.get('duration_ms', 0) for req in recent_requests]
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
    window: int = Query(15, description="Time window in minutes")
):
    """Get requests summary for dashboard cards"""
    return get_audit_summary(window)

@router.get("/admin/requests")
async def get_requests(
    limit: int = Query(500, ge=1, le=1000, description="Number of requests to return"),
    window: str = Query("15m", description="Time window (e.g., 15m, 1h, 24h)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Page size"),
    since: Optional[str] = Query(None, description="Start time (ISO format)"),
    until: Optional[str] = Query(None, description="End time (ISO format)"),
    method: Optional[str] = Query(None, description="HTTP method"),
    status: Optional[int] = Query(None, description="HTTP status code"),
    endpoint: Optional[str] = Query(None, description="API endpoint path"),
    client_ip: Optional[str] = Query(None, description="Client IP address"),
    api_key_prefix: Optional[str] = Query(None, description="API key prefix")
):
    """Get paginated audit records with enhanced filtering"""
    # Parse time window
    window_minutes = 15  # default
    if window.endswith('m'):
        try:
            window_minutes = int(window[:-1])
        except ValueError:
            pass
    elif window.endswith('h'):
        try:
            window_minutes = int(window[:-1]) * 60
        except ValueError:
            pass
    
    # Calculate time cutoff
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=window_minutes)
    
    # Use real audit data from memory
    filtered_data = in_memory_audit_logs.copy()
    
    # Apply time window filter
    filtered_data = [req for req in filtered_data if req.get('ts', now) >= cutoff]
    
    # Apply additional filters
    if since:
        since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
        filtered_data = [req for req in filtered_data if req.get('ts', datetime.utcnow()) >= since_dt]
    
    if until:
        until_dt = datetime.fromisoformat(until.replace('Z', '+00:00'))
        filtered_data = [req for req in filtered_data if req.get('ts', datetime.utcnow()) <= until_dt]
    
    if method:
        filtered_data = [req for req in filtered_data if req.get('method') == method.upper()]
    
    if status:
        filtered_data = [req for req in filtered_data if req.get('status') == status]
    
    if endpoint:
        filtered_data = [req for req in filtered_data if endpoint in req.get('path', '')]
    
    if client_ip:
        filtered_data = [req for req in filtered_data if client_ip in req.get('client_ip', '')]
    
    if api_key_prefix:
        filtered_data = [req for req in filtered_data if api_key_prefix in req.get('api_key_masked', '')]
    
    # Sort by timestamp (newest first)
    filtered_data.sort(key=lambda x: x.get('ts', now), reverse=True)
    
    # Apply limit
    filtered_data = filtered_data[:limit]
    
    # Pagination
    total = len(filtered_data)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    items = filtered_data[start_idx:end_idx]
    
    # Mask API keys for display
    for item in items:
        if 'api_key' in item:
            item['api_key_masked'] = mask_api_key(item['api_key'])
            del item['api_key']  # Don't expose raw keys
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "window_minutes": window_minutes,
        "window": window
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
    limit: int = Query(500, ge=1, le=1000, description="Number of requests to return"),
    window: str = Query("15m", description="Time window (e.g., 15m, 1h, 24h)")
):
    """Enhanced API endpoint for requests with aggregation by time window"""
    # Parse time window
    window_minutes = 15  # default
    if window.endswith('m'):
        try:
            window_minutes = int(window[:-1])
        except ValueError:
            pass
    elif window.endswith('h'):
        try:
            window_minutes = int(window[:-1]) * 60
        except ValueError:
            pass
    
    # Calculate time cutoff
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=window_minutes)
    
    # Use real audit data from memory
    recent_requests = [req for req in in_memory_audit_logs if req.get('ts', now) >= cutoff]
    
    # Sort by timestamp (newest first)
    recent_requests.sort(key=lambda x: x.get('ts', now), reverse=True)
    
    # Apply limit
    recent_requests = recent_requests[:limit]
    
    # Calculate aggregations for state boxes
    total_requests = len(recent_requests)
    succeeded = sum(1 for req in recent_requests if 200 <= req.get('status', 0) < 300)
    failed = sum(1 for req in recent_requests if req.get('status', 0) >= 400)
    
    # Calculate average latency
    latencies = [req.get('duration_ms', 0) for req in recent_requests if req.get('duration_ms', 0) > 0]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    # Prepare response data with enhanced fields for UI
    items = []
    for req in recent_requests:
        item = req.copy()
        
        # Mask API keys
        if 'api_key' in item:
            item['api_key_masked'] = mask_api_key(item['api_key'])
            del item['api_key']
        
        # Add computed fields for UI
        item['records'] = item.get('records_processed', 0)
        item['risk_avg'] = item.get('avg_risk_score', 0)
        item['latency_ms'] = item.get('duration_ms', 0)
        
        # Extract source IP for display
        item['source_ip'] = item.get('client_ip', 'unknown')
        
        items.append(item)
    
    return {
        "items": items,
        "total": total_requests,
        "succeeded": succeeded,
        "failed": failed,
        "avg_latency_ms": round(avg_latency, 2),
        "window_minutes": window_minutes,
        "window": window
    }
