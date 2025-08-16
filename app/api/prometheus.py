"""
Prometheus metrics endpoint for Telemetry API
"""

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse
from ..services.prometheus_metrics import prometheus_metrics

router = APIRouter(tags=["Metrics"])

@router.get("/metrics/prometheus", summary="Prometheus metrics")
async def get_prometheus_metrics() -> Response:
    """
    Get metrics in Prometheus exposition format.
    
    Returns metrics in plain text format suitable for Prometheus scraping.
    """
    metrics_data = prometheus_metrics.get_metrics()
    return PlainTextResponse(
        content=metrics_data,
        media_type=prometheus_metrics.get_content_type()
    )
