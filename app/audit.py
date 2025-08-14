"""
Request audit logging middleware and utilities
"""

import time
import hashlib
import hmac
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from collections import defaultdict
import asyncio
from contextlib import asynccontextmanager

# Simple in-memory audit storage for now
from .enrich.geo import enrich_geo_asn

# Global audit configuration
AUDIT_SALT = "telemetry-api-audit-2024"  # In production, use env var
AUDIT_RETENTION_DAYS = 7

# In-memory active clients tracking (15-minute window)
active_clients = defaultdict(set)  # {timestamp_minute: set of client_ips}
last_cleanup = time.time()

# In-memory audit storage (temporary, replaces database)
in_memory_audit_logs = []

# Request context for storing operations data
request_context = {}

# Counter for audit record IDs
audit_id_counter = 0

def hash_api_key(api_key: str) -> str:
    """Hash API key for storage"""
    return hmac.new(
        AUDIT_SALT.encode(),
        api_key.encode(),
        hashlib.sha256
    ).hexdigest()

def mask_api_key(api_key: str) -> str:
    """Mask API key for display (first 4 + last 4 chars)"""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}****{api_key[-4:]}"

def classify_result(status: int) -> str:
    """Classify request result based on status code"""
    if 200 <= status < 300:
        return "ok"
    elif status == 429:
        return "rate_limited"
    else:
        return "error"

def get_client_ip(request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def update_active_clients(client_ip: str):
    """Update active clients tracking"""
    global last_cleanup
    current_minute = int(time.time() // 60)
    
    # Add to current minute
    active_clients[current_minute].add(client_ip)
    
    # Cleanup old entries (keep 15 minutes)
    if time.time() - last_cleanup > 60:  # Cleanup every minute
        cutoff_minute = current_minute - 15
        for old_minute in list(active_clients.keys()):
            if old_minute < cutoff_minute:
                del active_clients[old_minute]
        last_cleanup = time.time()

def get_active_clients_count() -> int:
    """Get count of active clients in last 15 minutes"""
    current_minute = int(time.time() // 60)
    cutoff_minute = current_minute - 15
    
    unique_clients = set()
    for minute, clients in active_clients.items():
        if minute >= cutoff_minute:
            unique_clients.update(clients)
    
    return len(unique_clients)

@asynccontextmanager
async def audit_request(request, api_key: str, tenant_id: str):
    """Context manager for request auditing"""
    start_time = time.time()
    start_ts = datetime.utcnow()
    
    # Extract request info
    client_ip = get_client_ip(request)
    method = request.method
    path = request.url.path
    user_agent = request.headers.get("User-Agent", "")
    
    # Generate trace ID
    trace_id = str(uuid.uuid4())
    
    # Update active clients
    update_active_clients(client_ip)
    
    # Enrich client IP with Geo/ASN
    geo_info = enrich_geo_asn(client_ip) if client_ip != "unknown" else None
    geo_country = geo_info.get("geo", {}).get("country_code") if geo_info else None
    asn = geo_info.get("asn", {}).get("organization") if geo_info else None
    
    # Hash API key
    api_key_hash = hash_api_key(api_key)
    
    # Get content length
    content_length = request.headers.get("Content-Length", 0)
    bytes_in = int(content_length) if content_length else 0
    
    try:
        # Yield control back to request handler
        yield trace_id
        
    except Exception as e:
        # Log error
        logging.error(f"Request audit error: {e}")
        raise
    finally:
        # Calculate duration and response info
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Note: bytes_out would need to be captured from response
        # For now, we'll estimate based on typical response sizes
        bytes_out = 0  # TODO: capture from response
        
        # Create audit record (in-memory for now)
        audit_record = {
            'ts': start_ts,
            'tenant_id': tenant_id,
            'api_key_hash': api_key_hash,
            'client_ip': client_ip,
            'user_agent': user_agent,
            'method': method,
            'path': path,
            'status': 0,  # Will be updated by middleware
            'duration_ms': duration_ms,
            'bytes_in': bytes_in,
            'bytes_out': bytes_out,
            'result': "ok",  # Will be updated by middleware
            'trace_id': trace_id,
            'geo_country': geo_country,
            'asn': asn,
            'ops': None,  # Will be filled by handlers
            'error': None  # Will be filled by middleware
        }
        
        # Store audit record asynchronously
        asyncio.create_task(store_audit_record(audit_record))

async def store_audit_record(record: dict):
    """Store audit record asynchronously"""
    global audit_id_counter
    try:
        # Assign unique ID
        audit_id_counter += 1
        record['id'] = audit_id_counter
        
        # Add to in-memory audit logs
        in_memory_audit_logs.append(record)
        
        # Log it
        logging.info(f"AUDIT: {record['method']} {record['path']} - {record['client_ip']} - {record['duration_ms']}ms")
    except Exception as e:
        logging.error(f"Failed to store audit record: {e}")

def set_request_ops(trace_id: str, ops: dict):
    """Store operations data for a request"""
    request_context[trace_id] = ops

def get_request_ops(trace_id: str) -> dict:
    """Get operations data for a request"""
    return request_context.get(trace_id, {})

async def cleanup_old_audit_records():
    """Cleanup audit records older than retention period"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=AUDIT_RETENTION_DAYS)
        # TODO: Implement database cleanup
        logging.info(f"Cleaned up audit records older than {cutoff_date}")
    except Exception as e:
        logging.error(f"Failed to cleanup audit records: {e}")
