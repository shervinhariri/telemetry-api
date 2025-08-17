"""
Request Audit System
Maintains a ring buffer of request audits with timeline events.
"""

import os
import time
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# Global audit buffer (ring buffer with max 1000 entries)
AUDIT_BUFFER = deque(maxlen=1000)

@dataclass
class TimelineEvent:
    """Single timeline event"""
    ts: str
    event: str
    meta: Dict[str, Any]

@dataclass
class RequestAudit:
    """Complete request audit with timeline"""
    id: str
    ts: str
    method: str
    path: str
    client_ip: str
    tenant_id: str
    status: int
    latency_ms: float
    summary: Dict[str, Any]
    timeline: List[TimelineEvent]

def start_audit(trace_id: str, method: str, path: str, client_ip: str, 
                tenant_id: str = "unknown") -> RequestAudit:
    """Start a new request audit"""
    audit = RequestAudit(
        id=trace_id,
        ts=datetime.now(timezone.utc).isoformat(),
        method=method,
        path=path,
        client_ip=client_ip,
        tenant_id=tenant_id,
        status=0,
        latency_ms=0.0,
        summary={},
        timeline=[]
    )
    AUDIT_BUFFER.append(audit)
    return audit

def push_event(audit: RequestAudit, event: str, **meta):
    """Add a timeline event to the audit"""
    timeline_event = TimelineEvent(
        ts=datetime.now(timezone.utc).isoformat(),
        event=event,
        meta=meta
    )
    audit.timeline.append(timeline_event)

def complete_audit(audit: RequestAudit, status: int, latency_ms: float, **summary):
    """Complete the audit with final status and summary"""
    audit.status = status
    audit.latency_ms = latency_ms
    audit.summary.update(summary)

def get_recent_audits(limit: int = 50, status_filter: Optional[str] = None, 
                     endpoint_filter: Optional[str] = None, 
                     tenant_filter: Optional[str] = None,
                     trace_id_search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get recent audits with optional filtering"""
    audits = list(AUDIT_BUFFER)
    
    # Apply filters
    if status_filter:
        if status_filter == "2xx":
            audits = [a for a in audits if 200 <= a.status < 300]
        elif status_filter == "4xx":
            audits = [a for a in audits if 400 <= a.status < 500]
        elif status_filter == "5xx":
            audits = [a for a in audits if 500 <= a.status < 600]
    
    if endpoint_filter:
        audits = [a for a in audits if endpoint_filter in a.path]
    
    if tenant_filter:
        audits = [a for a in audits if tenant_filter == a.tenant_id]
    
    if trace_id_search:
        audits = [a for a in audits if trace_id_search.lower() in a.id.lower()]
    
    # Return most recent audits (limit)
    recent = audits[-limit:] if len(audits) > limit else audits
    
    # Convert to dict format for JSON serialization
    return [asdict(audit) for audit in recent]

def get_audit_stats() -> Dict[str, Any]:
    """Get audit buffer statistics"""
    audits = list(AUDIT_BUFFER)
    if not audits:
        return {"total": 0, "success_rate": 0, "avg_latency": 0}
    
    total = len(audits)
    successful = len([a for a in audits if 200 <= a.status < 300])
    success_rate = (successful / total * 100) if total > 0 else 0
    avg_latency = sum(a.latency_ms for a in audits) / total if total > 0 else 0
    
    return {
        "total": total,
        "success_rate": round(success_rate, 1),
        "avg_latency": round(avg_latency, 1)
    }
