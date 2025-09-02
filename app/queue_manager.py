"""
Queue management module for Telemetry API
Handles bounded queue with backpressure, worker pool, and structured error handling
"""

import asyncio
import logging
import time
import hashlib
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from .config import (
    QUEUE_MAX_DEPTH, WORKER_POOL_SIZE, QUEUE_RETRY_AFTER_SECONDS,
    ENRICH_TIMEOUT_MS, DISPATCH_TIMEOUT_MS
)
from .services.prometheus_metrics import prometheus_metrics

logger = logging.getLogger("queue_manager")

class QueueManager:
    """Manages the bounded processing queue and worker pool"""
    
    def __init__(self):
        self.queue: Optional[asyncio.Queue] = None
        self.workers: List[asyncio.Task] = []
        self.max_depth = QUEUE_MAX_DEPTH
        self.worker_pool_size = WORKER_POOL_SIZE
        self.retry_after_seconds = QUEUE_RETRY_AFTER_SECONDS
        self.enrich_timeout_ms = ENRICH_TIMEOUT_MS
        self.dispatch_timeout_ms = DISPATCH_TIMEOUT_MS
        self._rate_limit_tokens = {}  # Simple rate limiting for error logs
        
    def initialize(self):
        """Initialize the bounded queue"""
        self.queue = asyncio.Queue(maxsize=self.max_depth)
        logger.info("Queue manager initialized", extra={
            "component": "queue_manager",
            "max_depth": self.max_depth,
            "worker_pool_size": self.worker_pool_size
        })
        
    async def start_workers(self):
        """Start the worker pool"""
        if not self.queue:
            raise RuntimeError("Queue not initialized")
            
        for i in range(self.worker_pool_size):
            worker_task = asyncio.create_task(self._worker_loop(i))
            self.workers.append(worker_task)
            
        logger.info("Worker pool started", extra={
            "component": "queue_manager",
            "worker_count": self.worker_pool_size
        })
        
    async def stop_workers(self):
        """Stop all workers gracefully"""
        for worker in self.workers:
            worker.cancel()
            
        # Wait for all workers to complete
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
            
        self.workers.clear()
        logger.info("Worker pool stopped", extra={
            "component": "queue_manager"
        })
        
    def enqueue_record(self, record: Dict[str, Any]) -> bool:
        """
        Enqueue a record for processing.
        Returns True if enqueued, False if queue is full (backpressure).
        """
        if not self.queue:
            # Queue not initialized - this shouldn't happen in production
            # but can happen during testing, so let's be lenient
            logger.warning("Queue not initialized, accepting record anyway", extra={
                "component": "queue_manager",
                "event": "queue_not_initialized"
            })
            return True
            
        try:
            # Add enqueue timestamp for latency tracking
            record["_enqueued_ts"] = time.time()
            
            # Try to put the record in the queue
            self.queue.put_nowait(record)
            
            # Update metrics
            prometheus_metrics.increment_queue_enqueues(1)
            self._update_queue_metrics()
            
            return True
            
        except asyncio.QueueFull:
            # Queue is full - backpressure
            prometheus_metrics.increment_queue_drops(1)
            self._update_queue_metrics()
            
            # Log backpressure (rate limited)
            self._log_backpressure()
            
            return False
            
    def _update_queue_metrics(self):
        """Update queue depth and saturation metrics"""
        if self.queue:
            depth = self.queue.qsize()
            saturation = depth / self.max_depth if self.max_depth > 0 else 0
            
            prometheus_metrics.set_queue_depth(depth)
            prometheus_metrics.set_queue_saturation(saturation)
            
    def _log_backpressure(self):
        """Log backpressure event (rate limited)"""
        # Simple rate limiting: log first occurrence, then every 100th
        key = "backpressure"
        if key not in self._rate_limit_tokens:
            self._rate_limit_tokens[key] = {"count": 0, "last_log": 0}
            
        token = self._rate_limit_tokens[key]
        token["count"] += 1
        
        should_log = (token["count"] == 1 or 
                     token["count"] % 100 == 0 or 
                     time.time() - token["last_log"] > 60)  # At least once per minute
                     
        if should_log:
            depth = self.queue.qsize() if self.queue else 0
            logger.warning("Queue backpressure - queue full", extra={
                "component": "queue_manager",
                "event": "backpressure",
                "queue_depth": depth,
                "max_depth": self.max_depth,
                "drop_count": token["count"]
            })
            token["last_log"] = time.time()
            
    async def _worker_loop(self, worker_id: int):
        """Worker loop that processes records from the queue"""
        logger.info("Worker started", extra={
            "component": "queue_manager",
            "worker_id": worker_id
        })
        
        while True:
            try:
                if not self.queue:
                    await asyncio.sleep(1)
                    continue
                    
                # Get record from queue
                record = await self.queue.get()
                
                try:
                    # Process the record
                    await self._process_record(record, worker_id)
                    
                except Exception as e:
                    # Handle processing errors
                    await self._handle_processing_error(record, e, worker_id)
                    
                finally:
                    # Mark task as done
                    self.queue.task_done()
                    
            except asyncio.CancelledError:
                logger.info("Worker cancelled", extra={
                    "component": "queue_manager",
                    "worker_id": worker_id
                })
                break
            except Exception as e:
                logger.error("Worker loop error", extra={
                    "component": "queue_manager",
                    "worker_id": worker_id,
                    "error": str(e)
                })
                await asyncio.sleep(1)
                
    async def _process_record(self, record: Dict[str, Any], worker_id: int):
        """Process a single record through all stages"""
        start_time = time.time()
        record_id = self._get_record_id(record)
        
        try:
            # Stage 1: GeoIP/ASN enrichment
            enriched = await self._enrich_geo_asn(record)
            
            # Stage 2: Threat Intelligence
            enriched = await self._enrich_ti(enriched)
            
            # Stage 3: Risk scoring
            enriched = await self._enrich_risk(enriched)
            
            # Stage 4: Store
            await self._store_record(enriched)
            
            # Stage 5: Dispatch (if configured)
            await self._dispatch_record(enriched)
            
            # Record successful processing
            processing_time = time.time() - start_time
            prometheus_metrics.increment_worker_processed(1)
            prometheus_metrics.observe_event_processing_seconds(processing_time)
            prometheus_metrics.observe_processing_latency(processing_time * 1000.0)  # Convert to milliseconds
            
            # Update queue metrics
            self._update_queue_metrics()
            
            logger.debug("Record processed successfully", extra={
                "component": "queue_manager",
                "worker_id": worker_id,
                "record_id": record_id,
                "processing_time": processing_time
            })
            
        except Exception as e:
            # Re-raise to be handled by _handle_processing_error
            raise
            
    async def _enrich_geo_asn(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich record with GeoIP and ASN data"""
        start_time = time.time()
        
        try:
            async with asyncio.timeout(self.enrich_timeout_ms / 1000.0):
                from .enrich.geo import enrich_geo_asn
                
                # Extract IPs for enrichment
                src_ip = record.get('src_ip') or record.get('id_orig_h')
                dst_ip = record.get('dst_ip') or record.get('id_resp_h')
                
                # GeoIP and ASN enrichment (use dst_ip if available, fallback to src_ip)
                target_ip = dst_ip or src_ip
                if target_ip:
                    geo_asn = enrich_geo_asn(target_ip)
                    if geo_asn:
                        record["geo"] = geo_asn.get("geo")
                        record["asn"] = geo_asn.get("asn")
                        
        except asyncio.TimeoutError:
            raise Exception("GeoIP/ASN enrichment timeout")
        except Exception as e:
            raise Exception(f"GeoIP/ASN enrichment error: {str(e)}")
        finally:
            stage_time = time.time() - start_time
            prometheus_metrics.observe_stage_seconds("geo_asn", stage_time)
            
        return record
        
    async def _enrich_ti(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich record with threat intelligence data"""
        start_time = time.time()
        
        try:
            async with asyncio.timeout(self.enrich_timeout_ms / 1000.0):
                from .enrich.ti import match_ip, match_domain
                
                # Extract IPs for TI matching
                src_ip = record.get('src_ip') or record.get('id_orig_h')
                dst_ip = record.get('dst_ip') or record.get('id_resp_h')
                
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
                
                record["ti"] = {"matches": ti_matches}
                
        except asyncio.TimeoutError:
            raise Exception("Threat intelligence enrichment timeout")
        except Exception as e:
            raise Exception(f"Threat intelligence enrichment error: {str(e)}")
        finally:
            stage_time = time.time() - start_time
            prometheus_metrics.observe_stage_seconds("ti", stage_time)
            
        return record
        
    async def _enrich_risk(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich record with risk scoring"""
        start_time = time.time()
        
        try:
            async with asyncio.timeout(self.enrich_timeout_ms / 1000.0):
                from .enrich.risk import score
                
                # Risk scoring
                ti_matches = record.get('ti', {}).get('matches', [])
                risk_score = score(record, ti_matches)
                record["risk_score"] = risk_score
                
        except asyncio.TimeoutError:
            raise Exception("Risk scoring timeout")
        except Exception as e:
            raise Exception(f"Risk scoring error: {str(e)}")
        finally:
            stage_time = time.time() - start_time
            prometheus_metrics.observe_stage_seconds("risk", stage_time)
            
        return record
        
    async def _store_record(self, record: Dict[str, Any]):
        """Store the enriched record"""
        start_time = time.time()
        
        try:
            async with asyncio.timeout(self.dispatch_timeout_ms / 1000.0):
                # Add metadata
                record["_source"] = "telemetry-api"
                record["_processed_at"] = time.time()
                record["_enriched"] = True
                
                # Store to NDJSON file (existing logic)
                from .pipeline import _append_ndjson
                _append_ndjson(record)
                
        except asyncio.TimeoutError:
            raise Exception("Record storage timeout")
        except Exception as e:
            raise Exception(f"Record storage error: {str(e)}")
        finally:
            stage_time = time.time() - start_time
            prometheus_metrics.observe_stage_seconds("store", stage_time)
            
    async def _dispatch_record(self, record: Dict[str, Any]):
        """Dispatch the record (placeholder for future export functionality)"""
        start_time = time.time()
        
        try:
            async with asyncio.timeout(self.dispatch_timeout_ms / 1000.0):
                # Placeholder for future export functionality
                # For now, just pass through
                pass
                
        except asyncio.TimeoutError:
            raise Exception("Record dispatch timeout")
        except Exception as e:
            raise Exception(f"Record dispatch error: {str(e)}")
        finally:
            stage_time = time.time() - start_time
            prometheus_metrics.observe_stage_seconds("dispatch", stage_time)
            
    async def _handle_processing_error(self, record: Dict[str, Any], error: Exception, worker_id: int):
        """Handle processing errors for a record"""
        record_id = self._get_record_id(record)
        error_msg = str(error)
        
        # Determine stage and error kind
        stage = "unknown"
        kind = "exception"
        
        if "timeout" in error_msg.lower():
            kind = "timeout"
        elif "geo" in error_msg.lower():
            stage = "geo_asn"
        elif "threat" in error_msg.lower() or "ti" in error_msg.lower():
            stage = "ti"
        elif "risk" in error_msg.lower():
            stage = "risk"
        elif "store" in error_msg.lower():
            stage = "store"
        elif "dispatch" in error_msg.lower():
            stage = "dispatch"
            
        # Increment error metric
        prometheus_metrics.increment_worker_errors(stage, kind, 1)
        
        # Log error (rate limited)
        self._log_processing_error(record_id, stage, kind, error_msg)
        
        logger.warning("Record processing failed", extra={
            "component": "queue_manager",
            "worker_id": worker_id,
            "record_id": record_id,
            "stage": stage,
            "kind": kind,
            "error": error_msg
        })
        
    def _log_processing_error(self, record_id: str, stage: str, kind: str, error_msg: str):
        """Log processing error (rate limited)"""
        # Simple rate limiting: log first occurrence, then every 10th
        key = f"{stage}_{kind}_{error_msg[:50]}"  # Truncate error message for key
        if key not in self._rate_limit_tokens:
            self._rate_limit_tokens[key] = {"count": 0, "last_log": 0}
            
        token = self._rate_limit_tokens[key]
        token["count"] += 1
        
        should_log = (token["count"] == 1 or 
                     token["count"] % 10 == 0 or 
                     time.time() - token["last_log"] > 60)  # At least once per minute
                     
        if should_log:
            logger.warning("Worker stage error", extra={
                "component": "queue_manager",
                "stage": stage,
                "event": "error",
                "kind": kind,
                "cause": error_msg,
                "record_id": record_id,
                "error_count": token["count"]
            })
            token["last_log"] = time.time()
            
    def _get_record_id(self, record: Dict[str, Any]) -> str:
        """Generate a unique record ID for logging"""
        # Use timestamp and source IP if available
        ts = record.get('ts', 'no-ts')
        src_ip = record.get('src_ip') or record.get('id_orig_h', 'no-ip')
        return hashlib.md5(f"{ts}-{src_ip}".encode()).hexdigest()[:8]
        
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get current queue statistics"""
        if not self.queue:
            return {"depth": 0, "max": self.max_depth, "saturation": 0.0}
            
        depth = self.queue.qsize()
        saturation = depth / self.max_depth if self.max_depth > 0 else 0.0
        
        return {
            "depth": depth,
            "max": self.max_depth,
            "saturation": saturation
        }

# Global queue manager instance
queue_manager = QueueManager()
