"""
Idempotency Support for Ingest Endpoints
"""
import hashlib
import time
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

# In-memory storage for idempotency keys (in production, use Redis/database)
IDEMPOTENCY_CACHE: Dict[str, Dict[str, Any]] = {}

# Configuration
IDEMPOTENCY_TTL_HOURS = 24  # Keep idempotency keys for 24 hours

def generate_idempotency_key(payload: Any) -> str:
    """Generate idempotency key from payload"""
    if isinstance(payload, (dict, list)):
        payload_str = json.dumps(payload, sort_keys=True)
    else:
        payload_str = str(payload)
    
    return hashlib.sha256(payload_str.encode()).hexdigest()

def check_idempotency(idempotency_key: str) -> Optional[Dict[str, Any]]:
    """Check if request is duplicate and return cached response"""
    if idempotency_key in IDEMPOTENCY_CACHE:
        cached = IDEMPOTENCY_CACHE[idempotency_key]
        
        # Check if cache entry is still valid
        created_at = cached.get("created_at", 0)
        age_hours = (time.time() - created_at) / 3600
        
        if age_hours < IDEMPOTENCY_TTL_HOURS:
            logging.info(f"Idempotency hit for key: {idempotency_key[:8]}...")
            return cached.get("response")
        else:
            # Remove expired entry
            del IDEMPOTENCY_CACHE[idempotency_key]
    
    return None

def store_idempotency_result(idempotency_key: str, response: Dict[str, Any]) -> None:
    """Store response for idempotency"""
    IDEMPOTENCY_CACHE[idempotency_key] = {
        "response": response,
        "created_at": time.time()
    }
    
    # Clean up old entries
    cleanup_expired_entries()

def cleanup_expired_entries() -> None:
    """Clean up expired idempotency entries"""
    cutoff_time = time.time() - (IDEMPOTENCY_TTL_HOURS * 3600)
    expired_keys = []
    
    for key, entry in IDEMPOTENCY_CACHE.items():
        if entry.get("created_at", 0) < cutoff_time:
            expired_keys.append(key)
    
    for key in expired_keys:
        del IDEMPOTENCY_CACHE[key]
    
    if expired_keys:
        logging.info(f"Cleaned up {len(expired_keys)} expired idempotency entries")

def get_idempotency_stats() -> Dict[str, Any]:
    """Get idempotency cache statistics"""
    return {
        "total_entries": len(IDEMPOTENCY_CACHE),
        "ttl_hours": IDEMPOTENCY_TTL_HOURS
    }
