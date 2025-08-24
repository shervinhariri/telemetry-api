"""
Dead Letter Queue for Failed Exports
"""
import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

# Configuration
DLQ_DIR = Path(os.getenv("TELEMETRY_DLQ_DIR", "/tmp/dlq"))
DLQ_MAX_SIZE_MB = int(os.getenv("DLQ_MAX_SIZE_MB", "100"))  # 100MB default
DLQ_MAX_AGE_DAYS = int(os.getenv("DLQ_MAX_AGE_DAYS", "7"))  # 7 days default

class DeadLetterQueue:
    def __init__(self):
        self.dlq_dir = DLQ_DIR
        self.dlq_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = DLQ_MAX_SIZE_MB * 1024 * 1024
        self.max_age_seconds = DLQ_MAX_AGE_DAYS * 24 * 60 * 60
        
    def write_failed_export(self, 
                           events: List[Dict[str, Any]], 
                           destination: str, 
                           error: str, 
                           last_status: Optional[int] = None,
                           retry_count: int = 0) -> str:
        """Write failed export to DLQ"""
        timestamp = datetime.now()
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{destination}_{len(events)}_events.jsonl"
        filepath = self.dlq_dir / filename
        
        dlq_record = {
            "timestamp": timestamp.isoformat(),
            "destination": destination,
            "events_count": len(events),
            "error": error,
            "last_status": last_status,
            "retry_count": retry_count,
            "events": events
        }
        
        with open(filepath, 'w') as f:
            f.write(json.dumps(dlq_record) + '\n')
        
        logging.warning(f"Wrote {len(events)} failed events to DLQ: {filename}")
        return filename
    
    def get_dlq_stats(self) -> Dict[str, Any]:
        """Get DLQ statistics"""
        if not self.dlq_dir.exists():
            return {
                "total_files": 0,
                "total_events": 0,
                "total_size_mb": 0,
                "oldest_age_hours": 0
            }
        
        total_files = 0
        total_events = 0
        total_size = 0
        oldest_timestamp = None
        
        for filepath in self.dlq_dir.glob("*.jsonl"):
            try:
                total_files += 1
                total_size += filepath.stat().st_size
                
                # Read first line to get timestamp
                with open(filepath, 'r') as f:
                    first_line = f.readline()
                    if first_line:
                        record = json.loads(first_line)
                        timestamp_str = record.get("timestamp")
                        if timestamp_str:
                            timestamp = datetime.fromisoformat(timestamp_str)
                            if oldest_timestamp is None or timestamp < oldest_timestamp:
                                oldest_timestamp = timestamp
                        
                        total_events += record.get("events_count", 0)
                        
            except Exception as e:
                logging.error(f"Error reading DLQ file {filepath}: {e}")
        
        oldest_age_hours = 0
        if oldest_timestamp:
            age = datetime.now() - oldest_timestamp
            oldest_age_hours = age.total_seconds() / 3600
        
        return {
            "total_files": total_files,
            "total_events": total_events,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_age_hours": round(oldest_age_hours, 2)
        }
    
    def cleanup_old_records(self) -> int:
        """Clean up old DLQ records"""
        if not self.dlq_dir.exists():
            return 0
        
        cutoff_time = datetime.now() - timedelta(seconds=self.max_age_seconds)
        deleted_count = 0
        
        for filepath in self.dlq_dir.glob("*.jsonl"):
            try:
                # Check file modification time
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                if mtime < cutoff_time:
                    filepath.unlink()
                    deleted_count += 1
                    logging.info(f"Deleted old DLQ file: {filepath.name}")
            except Exception as e:
                logging.error(f"Error deleting DLQ file {filepath}: {e}")
        
        return deleted_count
    
    def check_size_limit(self) -> bool:
        """Check if DLQ is over size limit"""
        if not self.dlq_dir.exists():
            return False
        
        total_size = sum(f.stat().st_size for f in self.dlq_dir.glob("*.jsonl"))
        return total_size > self.max_size_bytes

# Global DLQ instance
dlq = DeadLetterQueue()
