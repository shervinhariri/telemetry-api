"""
Response builders for consistent error responses
Ensures exact JSON bodies and headers for all error cases
"""

from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
from ..config import QUEUE_RETRY_AFTER_SECONDS

def build_size_limit_response(content_encoding: str, actual_bytes: int) -> JSONResponse:
    """Build 413 Payload Too Large response for size limit exceeded"""
    return JSONResponse(
        status_code=413,
        content={
            "error": "batch_too_large",
            "limit_bytes": 5242880,  # 5 MB
            "content_encoding": content_encoding,
            "actual_bytes": actual_bytes
        }
    )

def build_count_limit_response(observed: int) -> JSONResponse:
    """Build 422 Unprocessable Entity response for record count exceeded"""
    return JSONResponse(
        status_code=422,
        content={
            "error": "too_many_records",
            "limit": 10000,
            "observed": observed
        }
    )

def build_shape_error_response() -> JSONResponse:
    """Build 422 Unprocessable Entity response for bad batch shape"""
    return JSONResponse(
        status_code=422,
        content={
            "error": "bad_batch_shape",
            "hint": "expected JSON array or JSONL"
        }
    )

def build_backpressure_response() -> JSONResponse:
    """Build 503 Service Unavailable response for queue backpressure"""
    return JSONResponse(
        status_code=503,
        content={
            "error": "backpressure",
            "retry_after": QUEUE_RETRY_AFTER_SECONDS
        },
        headers={"Retry-After": str(QUEUE_RETRY_AFTER_SECONDS)}
    )

def build_auth_error_response(status_code: int, detail: str) -> JSONResponse:
    """Build consistent auth error responses"""
    if status_code == 401:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "detail": detail
            }
        )
    elif status_code == 403:
        return JSONResponse(
            status_code=403,
            content={
                "error": "forbidden",
                "detail": detail
            }
        )
    else:
        return JSONResponse(
            status_code=status_code,
            content={
                "error": "authentication_error",
                "detail": detail
            }
        )

def build_validation_error_response(detail: str) -> JSONResponse:
    """Build 400 Bad Request response for validation errors"""
    return JSONResponse(
        status_code=400,
        content={
            "error": "validation_failed",
            "detail": detail
        }
    )

def build_json_error_response(detail: str) -> JSONResponse:
    """Build 400 Bad Request response for JSON parsing errors"""
    return JSONResponse(
        status_code=400,
        content={
            "error": "invalid_json",
            "detail": detail
        }
    )
