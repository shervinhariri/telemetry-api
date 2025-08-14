import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from collections import deque
import threading

# Import enrichment modules
from .enrich.geo import enrich_geo_asn
from .enrich.ti import match_ip, match_domain
from .enrich.risk import score

# Import metrics functions
from .metrics import record_event, record_queue_lag

# Global state (keeping for backward compatibility)
STATS = {
    "records_processed": 0,
    "batches_accepted": 0,
    "eps": 0.0,  # events per second
    "queue_depth": 0,
    "last_processed": None,
    "start_time": time.time()
}

# Ring buffer for recent events (last 1000)
RECENT_EVENTS = deque(maxlen=1000)

# Data directory
DATA_DIR = Path("/data")
DATA_DIR.mkdir(exist_ok=True)
(DATA_DIR / "uploads").mkdir(exist_ok=True)

# Ingest queue
ingest_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)

def record_batch_accepted(count: int):
    """Record that a batch was accepted"""
    STATS["batches_accepted"] += 1
    STATS["queue_depth"] = ingest_queue.qsize()
    # Also record in new metrics system
    from .metrics import record_batch
    record_batch(count, 0, [], [])  # count, threat_matches, risk_scores, sources

def enqueue(record: Dict[str, Any]):
    """Enqueue a record for processing"""
    try:
        # Add enqueue timestamp for lag tracking
        record["_enqueued_ts"] = int(time.time() * 1000)
        ingest_queue.put_nowait(record)
        STATS["queue_depth"] = ingest_queue.qsize()
    except asyncio.QueueFull:
        raise

def enqueue_batch(records: List[Dict[str, Any]]):
    """Enqueue a batch of records for processing"""
    enqueued = 0
    
    for record in records:
        try:
            enqueue(record)
            enqueued += 1
        except asyncio.QueueFull:
            break
    
    return enqueued

def _enrich_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich a single record with GeoIP, ASN, TI, and risk scoring"""
    enriched = record.copy()
    
    # Extract IPs for enrichment
    src_ip = record.get('src_ip') or record.get('id_orig_h')
    dst_ip = record.get('dst_ip') or record.get('id_resp_h')
    
    # GeoIP and ASN enrichment (use dst_ip if available, fallback to src_ip)
    target_ip = dst_ip or src_ip
    if target_ip:
        geo_asn = enrich_geo_asn(target_ip)
        if geo_asn:
            enriched["geo"] = geo_asn.get("geo")
            enriched["asn"] = geo_asn.get("asn")
    
    # Threat intelligence matching
    ti_matches = []
    if src_ip:
        ti_matches.extend(match_ip(src_ip))
    if dst_ip:
        ti_matches.extend(match_ip(dst_ip))
    
    # Domain matching if available
    domain = record.get('query') or record.get('dns_query')
    if domain:
        ti_matches.extend(match_domain(domain))
    
    enriched["ti"] = {"matches": ti_matches}
    
    # Risk scoring
    risk_score = score(record, ti_matches)
    enriched["risk_score"] = risk_score
    
    # Add metadata
    enriched["_source"] = "telemetry-api"
    enriched["_processed_at"] = datetime.now().isoformat()
    enriched["_enriched"] = True
    
    return enriched

def _append_ndjson(record: Dict[str, Any]):
    """Append enriched record to daily NDJSON file"""
    today = datetime.now().strftime("%Y-%m-%d")
    filename = DATA_DIR / f"events-{today}.ndjson"
    
    try:
        with open(filename, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        logging.error(f"Failed to write to {filename}: {e}")

def _update_stats():
    """Update statistics"""
    now = time.time()
    elapsed = now - STATS["start_time"]
    if elapsed > 0:
        STATS["eps"] = STATS["records_processed"] / elapsed
    STATS["queue_depth"] = ingest_queue.qsize()
    STATS["last_processed"] = datetime.now().isoformat()

async def worker_loop():
    """Background worker that processes records from the ingest queue"""
    logging.info("Pipeline worker started")
    
    while True:
        try:
            record = await ingest_queue.get()
            try:
                # Check for queue lag
                enqueued_ts = record.get("_enqueued_ts")
                if enqueued_ts:
                    lag_ms = int((time.time() * 1000) - enqueued_ts)
                    record_queue_lag(lag_ms)
                
                # Enrich the record
                enriched = _enrich_record(record)
                
                # Extract data for metrics
                ti_matches = enriched.get('ti', {}).get('matches', [])
                risk_score = enriched.get('risk_score', 0)
                src_ip = record.get('src_ip') or record.get('id_orig_h')
                
                # Record event for metrics (this now updates totals)
                record_event(risk_score, len(ti_matches))
                
                # Record unique sources
                if src_ip:
                    # Update unique sources directly
                    from .metrics import metrics
                    with metrics.lock:
                        metrics.totals["unique_sources"].add(src_ip)
                
                # Append to daily NDJSON
                _append_ndjson(enriched)
                
                # Add to recent events ring buffer
                RECENT_EVENTS.append(enriched)
                
                # Update statistics
                STATS["records_processed"] += 1
                
                _update_stats()
                
                logging.debug(f"Processed record: {record.get('ts', 'no-ts')}")
                
            except Exception as e:
                logging.exception(f"Worker failed processing record: {e}")
                # TODO: implement dead letter queue
            finally:
                ingest_queue.task_done()
                
        except Exception as e:
            logging.exception(f"Worker loop error: {e}")
            await asyncio.sleep(1)

def get_stats() -> Dict[str, Any]:
    """Get current statistics - now uses new metrics system"""
    from .metrics import get_metrics
    return get_metrics()

def get_recent_events(limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent processed events"""
    return list(RECENT_EVENTS)[-limit:]

def get_daily_events(date: str = None) -> str:
    """Get NDJSON content for a specific date"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    filename = DATA_DIR / f"events-{date}.ndjson"
    if not filename.exists():
        return ""
    
    try:
        with open(filename, "r") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to read {filename}: {e}")
        return ""
