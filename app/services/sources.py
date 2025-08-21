import json
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from app.models.source import Source
from app.schemas.source import SourceCreate, SourceUpdate, SourceMetrics
import ipaddress
import json
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models.source import Source

logger = logging.getLogger(__name__)


class SourceMetricsTracker:
    """In-memory tracker for source metrics"""
    
    def __init__(self):
        self.counters: Dict[str, Dict] = {}  # collector_id -> metrics
        self.last_flush = time.time()
        self.flush_interval = 10  # seconds
    
    def record_ingest(self, collector_id: str, record_count: int, success: bool, risk_score: float = 0.0):
        """Record an ingest operation for metrics calculation"""
        now = time.time()
        
        if collector_id not in self.counters:
            self.counters[collector_id] = {
                'records_1m': [],      # (timestamp, count) pairs
                'records_24h': 0,
                'errors_15m': [],      # (timestamp, error_count) pairs
                'risks_15m': [],       # (timestamp, risk_score) pairs
                'last_update': now
            }
        
        counter = self.counters[collector_id]
        
        # Record for 1-minute EPS calculation
        counter['records_1m'].append((now, record_count))
        counter['records_24h'] += record_count
        
        # Record for 15-minute error calculation
        if not success:
            counter['errors_15m'].append((now, 1))
        
        # Record for 15-minute risk calculation
        if risk_score > 0:
            counter['risks_15m'].append((now, risk_score))
        
        # Clean old data
        self._cleanup_old_data(counter, now)
    
    def _cleanup_old_data(self, counter: Dict, now: float):
        """Remove data older than the tracking windows"""
        # Keep only last 1 minute for EPS
        cutoff_1m = now - 60
        counter['records_1m'] = [(ts, count) for ts, count in counter['records_1m'] if ts > cutoff_1m]
        
        # Keep only last 15 minutes for errors and risk
        cutoff_15m = now - 900
        counter['errors_15m'] = [(ts, count) for ts, count in counter['errors_15m'] if ts > cutoff_15m]
        counter['risks_15m'] = [(ts, risk) for ts, risk in counter['risks_15m'] if ts > cutoff_15m]
    
    def get_metrics(self, collector_id: str) -> SourceMetrics:
        """Get current metrics for a collector"""
        now = time.time()
        
        if collector_id not in self.counters:
            return SourceMetrics()
        
        counter = self.counters[collector_id]
        
        # Calculate EPS (1 minute)
        total_records_1m = sum(count for _, count in counter['records_1m'])
        eps_1m = total_records_1m / 60.0 if counter['records_1m'] else 0.0
        
        # Calculate error percentage (15 minutes)
        total_errors_15m = sum(count for _, count in counter['errors_15m'])
        total_requests_15m = len(counter['errors_15m']) + max(1, len(counter['records_1m']) // 10)  # Estimate
        error_pct_15m = (total_errors_15m / total_requests_15m * 100) if total_requests_15m > 0 else 0.0
        
        # Calculate average risk (15 minutes)
        avg_risk_15m = 0.0
        if counter['risks_15m']:
            avg_risk_15m = sum(risk for _, risk in counter['risks_15m']) / len(counter['risks_15m'])
        
        return SourceMetrics(
            eps_1m=round(eps_1m, 2),
            records_24h=counter['records_24h'],
            error_pct_15m=round(error_pct_15m, 1),
            avg_risk_15m=round(avg_risk_15m, 2)
        )


# Global metrics tracker
metrics_tracker = SourceMetricsTracker()


class SourcesCache:
    """In-memory cache for source matching by exporter IP"""
    
    def __init__(self):
        self._sources = []
        self._last_refresh = 0
        self._refresh_interval = 30  # Refresh every 30 seconds
    
    def _should_refresh(self) -> bool:
        """Check if cache needs refresh"""
        import time
        return time.time() - self._last_refresh > self._refresh_interval
    
    def _refresh_cache(self):
        """Refresh the cache from database"""
        try:
            db = SessionLocal()
            try:
                # Get all enabled sources
                sources = db.query(Source).filter(Source.status == "enabled").all()
                self._sources = []
                
                for source in sources:
                    try:
                        # Parse allowed_ips for each source
                        allowed_ips = json.loads(source.allowed_ips)
                        if allowed_ips:  # Only cache sources with IP restrictions
                            self._sources.append({
                                'id': source.id,
                                'tenant_id': source.tenant_id,
                                'allowed_ips': allowed_ips,
                                'max_eps': source.max_eps,
                                'block_on_exceed': source.block_on_exceed,
                                'source_obj': source
                            })
                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning(f"Invalid allowed_ips for source {source.id}: {e}")
                        continue
                
                import time
                self._last_refresh = time.time()
                logger.debug(f"Refreshed sources cache with {len(self._sources)} sources")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to refresh sources cache: {e}")
    
    def match_by_exporter_ip(self, ip: str) -> Optional[Source]:
        """
        Find the best matching source for the given exporter IP.
        
        Args:
            ip: IP address of the exporter
            
        Returns:
            Source object if found, None otherwise
        """
        if self._should_refresh():
            self._refresh_cache()
        
        if not self._sources:
            return None
        
        # Find the best match (longest prefix match)
        best_match = None
        best_prefix_length = -1
        matches = []
        
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            for source_info in self._sources:
                for cidr_str in source_info['allowed_ips']:
                    try:
                        network = ipaddress.ip_network(cidr_str, strict=False)
                        if ip_obj in network:
                            prefix_length = network.prefixlen
                            matches.append((source_info, prefix_length))
                            
                            if prefix_length > best_prefix_length:
                                best_prefix_length = prefix_length
                                best_match = source_info
                    except ValueError:
                        logger.warning(f"Invalid CIDR in source {source_info['id']}: {cidr_str}")
                        continue
            
            # Log if multiple matches found
            if len(matches) > 1:
                logger.info(f"Multiple source matches for IP {ip}: {[m[0]['id'] for m in matches]}")
            
            return best_match['source_obj'] if best_match else None
            
        except ValueError:
            logger.warning(f"Invalid IP address: {ip}")
            return None
    
    def get_all_sources(self) -> List[Source]:
        """Get all cached sources (for debugging)"""
        if self._should_refresh():
            self._refresh_cache()
        return [s['source_obj'] for s in self._sources]

# Global cache instance
sources_cache = SourcesCache()


class SourceService:
    """Service for managing sources"""
    
    @staticmethod
    def create_source(db: Session, source_data: SourceCreate, tenant_id: str) -> Source:
        """Create a new source"""
        source = Source(
            id=source_data.id,
            tenant_id=tenant_id,
            type=source_data.type,
            display_name=source_data.display_name,
            collector=source_data.collector,
            site=source_data.site,
            tags=source_data.tags,
            notes=source_data.notes,
            health_status="stale",
            status=source_data.status or "enabled",
            allowed_ips=source_data.allowed_ips or "[]",
            max_eps=source_data.max_eps or 0,
            block_on_exceed=source_data.block_on_exceed if source_data.block_on_exceed is not None else True
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        return source
    
    @staticmethod
    def get_sources(
        db: Session, 
        tenant_id: str,
        source_type: Optional[str] = None,
        health_status: Optional[str] = None,
        site: Optional[str] = None,
        page: int = 1,
        size: int = 50
    ) -> Tuple[List[Source], int]:
        """Get paginated list of sources with filters"""
        query = db.query(Source).filter(Source.tenant_id == tenant_id)
        
        if source_type:
            query = query.filter(Source.type == source_type)
        if health_status:
            query = query.filter(Source.health_status == health_status)
        if site:
            query = query.filter(Source.site == site)
        
        total = query.count()
        sources = query.offset((page - 1) * size).limit(size).all()
        
        return sources, total
    
    @staticmethod
    def get_source_by_id(db: Session, source_id: str, tenant_id: str) -> Optional[Source]:
        """Get a source by ID"""
        return db.query(Source).filter(
            and_(Source.id == source_id, Source.tenant_id == tenant_id)
        ).first()
    
    @staticmethod
    def get_source_by_id_admin(db: Session, source_id: str) -> Optional[Source]:
        """Get a source by ID (admin access - no tenant restriction)"""
        return db.query(Source).filter(Source.id == source_id).first()
    
    @staticmethod
    def update_source_last_seen(db: Session, collector_id: str, tenant_id: str):
        """Update last_seen timestamp for sources using this collector"""
        now = datetime.utcnow()
        db.query(Source).filter(
            and_(Source.collector == collector_id, Source.tenant_id == tenant_id)
        ).update({"last_seen": now})
        db.commit()
    
    @staticmethod
    def track_source_origin(db: Session, source_id: str, tenant_id: str, traffic_origin: str):
        """
        Track the actual origin of traffic for a source and detect type mismatches
        
        Args:
            db: Database session
            source_id: Source identifier
            tenant_id: Tenant identifier
            traffic_origin: Actual origin of traffic ("udp", "http", "unknown")
        """
        from .prometheus_metrics import prometheus_metrics
        
        # Get the source
        source = SourceService.get_source_by_id(db, source_id, tenant_id)
        if not source:
            return
        
        # If origin is not set yet, set it based on first traffic
        if not source.origin:
            source.origin = traffic_origin
            db.commit()
            logger.info(f"Set origin for source {source_id} to {traffic_origin}")
            return
        
        # If origin is already set, check for type mismatch
        if source.origin != traffic_origin:
            # Traffic origin changed - this is unusual but not necessarily wrong
            logger.warning(f"Source {source_id} traffic origin changed from {source.origin} to {traffic_origin}")
            return
        
        # Check for type mismatch (declared type vs actual origin)
        if source.type != source.origin:
            # Increment mismatch metric
            prometheus_metrics.increment_source_type_mismatch(source_id)
            logger.warning(f"Source type mismatch for {source_id}: declared={source.type}, actual={source.origin}")
    
    @staticmethod
    def update_source_statuses(db: Session):
        """Update source statuses based on last_seen and metrics"""
        now = datetime.utcnow()
        
        # Get all sources
        sources = db.query(Source).all()
        
        for source in sources:
            if not source.last_seen:
                source.health_status = "stale"
                continue
            
            # Get metrics for this collector
            metrics = metrics_tracker.get_metrics(source.collector)
            
            # Calculate time since last seen
            time_diff = (now - source.last_seen).total_seconds()
            
            # Status rules
            if time_diff < 120 and metrics.error_pct_15m < 5.0:
                source.health_status = "healthy"
            elif time_diff < 300 or metrics.error_pct_15m >= 5.0:
                source.health_status = "degraded"
            else:
                source.health_status = "stale"
        
        db.commit()
    
    @staticmethod
    def record_ingest_metrics(collector_id: str, record_count: int, success: bool, risk_score: float = 0.0):
        """Record ingest metrics for a collector"""
        metrics_tracker.record_ingest(collector_id, record_count, success, risk_score)
    
    @staticmethod
    def get_source_metrics(collector_id: str, last_seen: Optional[datetime] = None) -> SourceMetrics:
        """Get metrics for a source"""
        metrics = metrics_tracker.get_metrics(collector_id)
        
        # Add last_seen if provided
        if last_seen:
            metrics.last_seen = last_seen.isoformat()
        
        return metrics
    
    @staticmethod
    def update_source(db: Session, source_id: str, update_data: dict) -> Source:
        """Update a source with new data"""
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise ValueError("Source not found")
        
        # Update allowed fields
        if 'display_name' in update_data:
            source.display_name = update_data['display_name']
        if 'status' in update_data:
            source.status = update_data['status']
        if 'allowed_ips' in update_data:
            # Ensure allowed_ips is stored as JSON string
            if isinstance(update_data['allowed_ips'], list):
                source.allowed_ips = json.dumps(update_data['allowed_ips'])
            else:
                source.allowed_ips = update_data['allowed_ips']
        if 'max_eps' in update_data:
            source.max_eps = update_data['max_eps']
        if 'block_on_exceed' in update_data:
            source.block_on_exceed = update_data['block_on_exceed']
        
        db.commit()
        db.refresh(source)
        return source
    
    @staticmethod
    def delete_source(db: Session, source_id: str):
        """Delete a source"""
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise ValueError("Source not found")
        
        db.delete(source)
        db.commit()
