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

# Global state
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

def enqueue(record: Dict[str, Any]):
    """Enqueue a record for processing"""
    try:
        ingest_queue.put_nowait(record)
        STATS["queue_depth"] = ingest_queue.qsize()
    except asyncio.QueueFull:
        raise

def _append_ndjson(record: Dict[str, Any]):
    """Append enriched record to daily NDJSON file"""
    today = datetime.now().strftime("%Y-%m-%d")
    filename = DATA_DIR / f"events-{today}.ndjson"
    
    # Add metadata
    enriched = {
        **record,
        "_source": "telemetry-api",
        "_processed_at": datetime.now().isoformat(),
        "_risk_score": 50,  # TODO: implement actual scoring
    }
    
    try:
        with open(filename, "a") as f:
            f.write(json.dumps(enriched) + "\n")
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
                # Basic enrichment (placeholder for now)
                enriched = {
                    **record,
                    "_enriched": True,
                    "_processed_at": datetime.now().isoformat()
                }
                
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
    """Get current statistics"""
    _update_stats()
    return STATS.copy()

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
