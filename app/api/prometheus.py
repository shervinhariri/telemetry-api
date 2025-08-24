"""
Prometheus metrics endpoint for Telemetry API
"""

import logging
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
    try:
        metrics_data = prometheus_metrics.get_metrics()
        return PlainTextResponse(
            content=metrics_data,
            media_type=prometheus_metrics.get_content_type()
        )
    except Exception as e:
        logging.error(f"Failed to get metrics: {e}")
        return PlainTextResponse(
            content="# Metrics temporarily unavailable\n",
            media_type="text/plain"
        )
