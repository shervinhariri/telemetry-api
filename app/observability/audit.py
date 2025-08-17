# app/observability/audit.py
from __future__ import annotations
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import os
import re

# Configuration from environment
MAX_AUDIT = int(os.getenv("ADMIN_AUDIT_MAX", "1000"))
AUDIT_TTL_MINUTES = int(os.getenv("ADMIN_AUDIT_TTL_MINUTES", "60"))
AUDIT: "deque[Dict[str, Any]]" = deque(maxlen=MAX_AUDIT)

MONITORING_PATHS = {"/v1/metrics", "/v1/system", "/v1/logs/tail", "/v1/admin/requests"}

# Redaction configuration
REDACT_HEADERS = set(os.getenv("REDACT_HEADERS", "authorization,x-api-key").split(","))
REDACT_FIELDS = set(os.getenv("REDACT_FIELDS", "password,token").split(","))

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def new_audit(
    trace_id: str,
    method: str,
    path: str,
    client_ip: Optional[str],
    tenant_id: str = "unknown",
) -> Dict[str, Any]:
    obj = {
        "id": trace_id,
        "ts": now_iso(),
        "method": method,
        "path": path,
        "client_ip": client_ip,
        "tenant_id": tenant_id,
        "status": None,
        "latency_ms": None,
        "summary": {},
        "timeline": [],   # up to 6 events max
        "fitness": None,  # 0..1 computed at completion
    }
    AUDIT.append(obj)
    return obj

def redact_sensitive_data(data: Any) -> Any:
    """Recursively redact sensitive data from audit events"""
    if isinstance(data, dict):
        redacted = {}
        for key, value in data.items():
            # Redact sensitive field names
            if any(sensitive in key.lower() for sensitive in REDACT_FIELDS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_sensitive_data(value)
        return redacted
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    elif isinstance(data, str):
        # Redact sensitive patterns in strings
        for sensitive in REDACT_FIELDS:
            if sensitive in data.lower():
                return "[REDACTED]"
        return data
    else:
        return data

def push_event(audit: Dict[str, Any], event: str, meta: Optional[Dict[str, Any]] = None) -> None:
    # Enforce max of 6 canonical events
    if len(audit["timeline"]) >= 6:
        return
    
    # Redact sensitive data before storing
    redacted_meta = redact_sensitive_data(meta or {})
    
    audit["timeline"].append({
        "ts": now_iso(),
        "event": event,
        "meta": redacted_meta
    })

def compute_fitness(audit: Dict[str, Any]) -> float:
    """
    Start at 1.0. Penalize validation failure and each failed export target.
    Clamp [0,1].
    """
    score = 1.0
    # validation penalty
    for step in audit["timeline"]:
        if step["event"] == "validated":
            ok = bool(step["meta"].get("ok", True))
            if not ok:
                score -= 0.4
        if step["event"] == "exported":
            for target in ("splunk", "elastic"):
                val = step["meta"].get(target)
                if val and str(val).lower() not in ("ok", "success", "true"):
                    score -= 0.2
    # final status penalty (if 4xx/5xx and not already covered)
    status = audit.get("status")
    if isinstance(status, int) and status >= 400:
        score = min(score, 0.59)  # force red if error
    return max(0.0, min(1.0, score))

def finalize_audit(
    audit: Dict[str, Any],
    status: int,
    latency_ms: float,
    summary: Optional[Dict[str, Any]] = None
) -> None:
    audit["status"] = status
    audit["latency_ms"] = round(float(latency_ms), 3)
    if summary:
        audit["summary"] = summary
    # Ensure "completed" exists
    has_completed = any(s["event"] == "completed" for s in audit["timeline"])
    if not has_completed:
        push_event(audit, "completed", {"status": status, "latency_ms": audit["latency_ms"]})
    audit["fitness"] = compute_fitness(audit)

def prune_expired_audits() -> None:
    """Remove audits older than TTL"""
    if AUDIT_TTL_MINUTES <= 0:
        return
    
    cutoff = datetime.now(timezone.utc).timestamp() - (AUDIT_TTL_MINUTES * 60)
    expired_count = 0
    
    # Remove expired audits from the end (oldest)
    while AUDIT:
        oldest = AUDIT[0]
        try:
            audit_time = datetime.fromisoformat(oldest.get("ts", "")).timestamp()
            if audit_time < cutoff:
                AUDIT.popleft()
                expired_count += 1
            else:
                break
        except (ValueError, TypeError):
            # Invalid timestamp, remove it
            AUDIT.popleft()
            expired_count += 1
    
    if expired_count > 0:
        import logging
        logging.info(f"Pruned {expired_count} expired audit records")

def list_audits(
    limit: int = 50,
    exclude_monitoring: bool = True,
    status_filter: str = "any",
    path_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    # Prune expired audits first
    prune_expired_audits()
    
    items = list(AUDIT)
    if exclude_monitoring:
        items = [x for x in items if x.get("path") not in MONITORING_PATHS]
    if status_filter in ("2xx", "4xx", "5xx"):
        def matches(status: Optional[int]) -> bool:
            if not isinstance(status, int): return False
            if status_filter == "2xx": return 200 <= status < 300
            if status_filter == "4xx": return 400 <= status < 500
            if status_filter == "5xx": return 500 <= status < 600
            return True
        items = [x for x in items if matches(x.get("status"))]
    if path_filter:
        items = [x for x in items if str(x.get("path","")).startswith(path_filter)]
    return items[-limit:]
