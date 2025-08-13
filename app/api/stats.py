from fastapi import APIRouter, Query
from typing import Optional
from ..pipeline import get_stats, get_recent_events, get_daily_events

router = APIRouter()

@router.get("/stats")
def get_processing_stats():
    """Get processing pipeline statistics"""
    return get_stats()

@router.get("/events/recent")
def get_recent_processed_events(limit: int = Query(100, ge=1, le=1000)):
    """Get recent processed events from ring buffer"""
    return {
        "events": get_recent_events(limit),
        "count": len(get_recent_events(limit))
    }

@router.get("/download")
def download_processed_events(date: Optional[str] = None):
    """Download processed events as NDJSON for a specific date (today by default)"""
    from fastapi.responses import Response
    
    content = get_daily_events(date)
    if not content:
        return {"error": "No data found for date", "date": date}
    
    filename = f"events-{date or 'today'}.ndjson"
    return Response(
        content=content,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
