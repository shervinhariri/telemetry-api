"""
Security and Privacy Features
"""
import os
import re
import ipaddress
import time
import threading
import json
from collections import defaultdict
from typing import Dict, Any, List, Optional
import logging

# Configuration
REDACT_HEADERS = os.getenv("REDACT_HEADERS", "authorization,x-forwarded-for").lower().split(",")
REDACT_FIELDS = os.getenv("REDACT_FIELDS", "user,email,hostname").lower().split(",")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

def redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Redact sensitive headers"""
    redacted = headers.copy()
    for header in REDACT_HEADERS:
        header_lower = header.strip().lower()
        for key in redacted:
            if key.lower() == header_lower:
                redacted[key] = "[REDACTED]"
    return redacted

def redact_payload(payload: Any) -> Any:
    """Recursively redact sensitive fields from payload"""
    if isinstance(payload, dict):
        redacted = {}
        for key, value in payload.items():
            key_lower = key.lower()
            if any(field in key_lower for field in REDACT_FIELDS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_payload(value)
        return redacted
    elif isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    else:
        return payload

def get_cors_headers() -> Dict[str, str]:
    """Get CORS headers"""
    return {
        "Access-Control-Allow-Origin": "*" if "*" in CORS_ORIGINS else ", ".join(CORS_ORIGINS),
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
        "Access-Control-Max-Age": "86400",
    }

def get_security_headers() -> Dict[str, str]:
    """Get security headers"""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    }

def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize data for logging"""
    sanitized = data.copy()
    
    # Redact headers
    if "headers" in sanitized:
        sanitized["headers"] = redact_headers(sanitized["headers"])
    
    # Redact payload
    if "payload" in sanitized:
        sanitized["payload"] = redact_payload(sanitized["payload"])
    
    # Redact request body
    if "body" in sanitized:
        sanitized["body"] = redact_payload(sanitized["body"])
    
    return sanitized


# ============================================================================
# Admission Control and Rate Limiting
# ============================================================================

class TokenBucket:
    """Token bucket rate limiter for per-source EPS limiting"""
    
    def __init__(self, rate_per_sec: int, burst: Optional[int] = None):
        self.rate = max(rate_per_sec, 0)
        self.capacity = burst if burst is not None else max(rate_per_sec, 1) * 2
        self.tokens = self.capacity
        self.timestamp = time.monotonic()
        self.lock = threading.Lock()

    def allow(self, n: int = 1) -> bool:
        """Check if n tokens can be consumed, consume them if possible"""
        with self.lock:
            now = time.monotonic()
            delta = now - self.timestamp
            self.timestamp = now
            
            # Add tokens based on time elapsed
            self.tokens = min(self.capacity, self.tokens + delta * self.rate)
            
            # Check if we have enough tokens
            if self.tokens >= n:
                self.tokens -= n
                return True
            return False


def ip_in_cidrs(ip: str, cidrs: List[str]) -> bool:
    """Check if IP is in any of the provided CIDR ranges"""
    from .config import get_admission_compat_allow_empty_ips
    
    if not cidrs:  # empty list
        # Handle empty allowed_ips based on compatibility flag
        return get_admission_compat_allow_empty_ips()  # True = allow-any (legacy), False = block-all (secure)
    
    try:
        ip_obj = ipaddress.ip_address(ip)
        for cidr in cidrs:
            if ip_obj in ipaddress.ip_network(cidr, strict=False):
                return True
        return False
    except ValueError:
        # Invalid IP or CIDR format
        return False


# Token buckets keyed per source_id
_buckets: dict[str, TokenBucket] = defaultdict(lambda: TokenBucket(0))


def get_bucket(source_id: str, max_eps: int) -> TokenBucket:
    """Get or create token bucket for a source"""
    b = _buckets.get(source_id)
    if b is None or b.rate != max_eps:
        b = TokenBucket(rate_per_sec=max(0, max_eps))
        _buckets[source_id] = b
    return b


def get_client_ip(request, trust_proxy: bool = False) -> str:
    """Extract client IP from request, handling X-Forwarded-For if trusted"""
    if trust_proxy:
        # Take first XFF element only if remote addr is in trusted proxies
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
    
    # Fallback to direct client IP
    return request.client.host if request.client else "127.0.0.1"


def validate_source_admission(
    source,
    client_ip: str,
    record_count: int = 1
) -> tuple[bool, str]:
    """
    Validate source admission based on security rules
    
    Returns:
        (allowed: bool, reason: str)
    """
    # Check if source is enabled
    if source.status != "enabled":
        return False, "disabled"
    
    # Check IP allowlist
    try:
        allowed_ips = json.loads(source.allowed_ips) if source.allowed_ips else []
    except (json.JSONDecodeError, TypeError):
        allowed_ips = []
    
    if not ip_in_cidrs(client_ip, allowed_ips):
        return False, "ip_not_allowed"
    
    # Check rate limiting
    max_eps = int(source.max_eps or 0)
    if max_eps > 0 and source.block_on_exceed:
        bucket = get_bucket(source.id, max_eps)
        if not bucket.allow(record_count):
            return False, "rate_limit"
    
    return True, "allowed"


def admission_should_block_udp(source_obj, exporter_ip: str) -> tuple[bool, str | None]:
    """
    Check if UDP packet from exporter_ip should be blocked based on source configuration.
    
    Args:
        source_obj: Source object from database
        exporter_ip: IP address of the exporter sending UDP packets
        
    Returns:
        (block: bool, reason: str | None) - True if should block, reason for blocking
    """
    from .config import (
        get_admission_udp_enabled, get_admission_log_only, 
        get_admission_fail_open, get_admission_compat_allow_empty_ips
    )
    
    # Check if UDP admission control is enabled
    if not get_admission_udp_enabled():
        return False, None
    
    try:
        # Check if source is enabled
        if source_obj.status != "enabled":
            return True, "disabled"
        
        # Check IP allowlist
        allowed_ips = json.loads(source_obj.allowed_ips)
        if not ip_in_cidrs(exporter_ip, allowed_ips):
            return True, "ip_not_allowed"
        
        # Check rate limiting if enabled
        if source_obj.max_eps > 0 and source_obj.block_on_exceed:
            bucket = get_bucket(source_obj.id)
            if not bucket.consume(1):
                return True, "rate_limit"
        
        return False, None
        
    except Exception as e:
        # Handle internal errors in admission control
        if get_admission_fail_open():
            return False, None  # Allow on error if FAIL_OPEN is enabled
        else:
            raise  # Re-raise the exception if FAIL_OPEN is disabled
