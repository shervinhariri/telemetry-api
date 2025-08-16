"""
Security and Privacy Features
"""
import os
import re
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
