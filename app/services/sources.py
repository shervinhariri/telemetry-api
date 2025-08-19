import json
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from app.models.source import Source
from app.schemas.source import SourceCreate, SourceUpdate, SourceMetrics



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
            status="stale"
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
        status: Optional[str] = None,
        site: Optional[str] = None,
        page: int = 1,
        size: int = 50
    ) -> Tuple[List[Source], int]:
        """Get paginated list of sources with filters"""
        query = db.query(Source).filter(Source.tenant_id == tenant_id)
        
        if source_type:
            query = query.filter(Source.type == source_type)
        if status:
            query = query.filter(Source.status == status)
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
    def update_source_last_seen(db: Session, collector_id: str, tenant_id: str):
        """Update last_seen timestamp for sources using this collector"""
        now = datetime.utcnow()
        db.query(Source).filter(
            and_(Source.collector == collector_id, Source.tenant_id == tenant_id)
        ).update({"last_seen": now})
        db.commit()
    
    @staticmethod
    def update_source_statuses(db: Session):
        """Update source statuses based on last_seen and metrics"""
        now = datetime.utcnow()
        
        # Get all sources
        sources = db.query(Source).all()
        
        for source in sources:
            if not source.last_seen:
                source.status = "stale"
                continue
            
            # Get metrics for this collector
            metrics = metrics_tracker.get_metrics(source.collector)
            
            # Calculate time since last seen
            time_diff = (now - source.last_seen).total_seconds()
            
            # Status rules
            if time_diff < 120 and metrics.error_pct_15m < 5.0:
                source.status = "healthy"
            elif time_diff < 300 or metrics.error_pct_15m >= 5.0:
                source.status = "degraded"
            else:
                source.status = "stale"
        
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
