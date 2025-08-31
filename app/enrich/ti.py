"""
Threat Intelligence enrichment module
Loads IP and domain threat lists from local files and HTTP sources
"""

import os
import time
import logging
import json
import csv
from typing import Dict, Any, Optional, List
from .base import EnrichmentLoader

from typing import Optional
from pydantic import BaseModel, IPvAnyNetwork
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.orm import Session

from ..db import Base, engine, get_db

class IndicatorModel(BaseModel):
    ip_or_cidr: IPvAnyNetwork
    category: str
    confidence: int

# If you have a proper ORM model, use it; otherwise a simple table via SQLAlchemy Core works.
from ..models.indicator import Indicator  # prefer a model if it exists

logger = logging.getLogger("enrich.ti")

class ThreatIntelLoader(EnrichmentLoader):
    """Threat Intelligence loader"""
    
    def __init__(self):
        super().__init__("threatintel")
        self.data_dir = os.getenv("TI_DATA_DIR", "/app/data/ti")
        self.sources = []
        self.ip_lists = {}
        self.domain_lists = {}
        
    def load(self) -> bool:
        """Load threat intelligence data"""
        try:
            # Load from local files
            self._load_local_files()
            
            # Load from HTTP sources (placeholder)
            self._load_http_sources()
            
            self.loaded = True
            self.last_refresh = time.time()
            
            # Update metrics
            from ..services.prometheus_metrics import prometheus_metrics
            prometheus_metrics.set_threatintel_loaded(True)
            prometheus_metrics.set_threatintel_sources(len(self.sources))
            
            logger.info(f"Threat intelligence loaded: {len(self.sources)} sources")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load threat intelligence: {e}")
            self.loaded = False
            return False
    
    def _load_local_files(self):
        """Load threat lists from local files"""
        if not os.path.exists(self.data_dir):
            logger.warning(f"Threat intelligence data directory not found: {self.data_dir}")
            return
        
        # Load IP lists
        ip_dir = os.path.join(self.data_dir, "ips")
        if os.path.exists(ip_dir):
            for filename in os.listdir(ip_dir):
                if filename.endswith(('.csv', '.txt', '.json')):
                    self._load_ip_list(os.path.join(ip_dir, filename))
        
        # Load domain lists
        domain_dir = os.path.join(self.data_dir, "domains")
        if os.path.exists(domain_dir):
            for filename in os.listdir(domain_dir):
                if filename.endswith(('.csv', '.txt', '.json')):
                    self._load_domain_list(os.path.join(domain_dir, filename))
    
    def _load_ip_list(self, filepath: str):
        """Load IP list from file"""
        try:
            filename = os.path.basename(filepath)
            ips = set()
            
            if filepath.endswith('.json'):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    # Handle various JSON formats
                    if isinstance(data, list):
                        ips.update(data)
                    elif isinstance(data, dict):
                        ips.update(data.get('ips', []))
                        ips.update(data.get('addresses', []))
            else:
                # CSV or TXT format
                with open(filepath, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            ips.add(line)
            
            self.ip_lists[filename] = ips
            self.sources.append(f"local:{filename}")
            
            logger.info(f"Loaded IP list {filename}: {len(ips)} entries")
            
        except Exception as e:
            logger.error(f"Failed to load IP list {filepath}: {e}")
    
    def _load_domain_list(self, filepath: str):
        """Load domain list from file"""
        try:
            filename = os.path.basename(filepath)
            domains = set()
            
            if filepath.endswith('.json'):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        domains.update(data)
                    elif isinstance(data, dict):
                        domains.update(data.get('domains', []))
            else:
                with open(filepath, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            domains.add(line)
            
            self.domain_lists[filename] = domains
            self.sources.append(f"local:{filename}")
            
            logger.info(f"Loaded domain list {filename}: {len(domains)} entries")
            
        except Exception as e:
            logger.error(f"Failed to load domain list {filepath}: {e}")
    
    def _load_http_sources(self):
        """Load threat lists from HTTP sources (placeholder)"""
        # This is a placeholder - in production, you'd implement HTTP fetching
        # with proper caching and error handling
        logger.info("HTTP threat intelligence sources not implemented yet")
    
    def match_ip(self, ip: str) -> List[Dict[str, Any]]:
        """Match IP against threat lists"""
        if not self.loaded:
            return []
        
        matches = []
        
        for source, ip_list in self.ip_lists.items():
            if ip in ip_list:
                matches.append({
                    "type": "ip",
                    "source": source,
                    "value": ip,
                    "category": "malicious"  # Default category
                })
        
        return matches
    
    def match_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Match domain against threat lists"""
        if not self.loaded:
            return []
        
        matches = []
        
        for source, domain_list in self.domain_lists.items():
            if domain in domain_list:
                matches.append({
                    "type": "domain",
                    "source": source,
                    "value": domain,
                    "category": "malicious"  # Default category
                })
        
        return matches
    
    def lookup(self, key: str) -> Optional[Dict[str, Any]]:
        """Lookup enrichment data for a key (alias for match_ip)"""
        matches = self.match_ip(key)
        return matches[0] if matches else None
    
    def get_status(self) -> Dict[str, Any]:
        """Get threat intelligence status"""
        status = super().get_status()
        status.update({
            "sources": self.sources,
            "ip_lists": len(self.ip_lists),
            "domain_lists": len(self.domain_lists)
        })
        return status

# Global loader instance
ti_loader = ThreatIntelLoader()

def match_ip(ip: str) -> List[Dict[str, Any]]:
    """Match IP against threat intelligence"""
    return ti_loader.match_ip(ip)

def match_domain(domain: str) -> List[Dict[str, Any]]:
    """Match domain against threat intelligence"""
    return ti_loader.match_domain(domain)

def initialize_threatintel():
    """Initialize threat intelligence loader"""
    ti_loader.load()

# In-memory storage for indicators (in production, this would be a database)
_indicators = {}
_indicator_counter = 0

def add_indicator(db: Session, model: IndicatorModel):
    row = Indicator(
        ip_or_cidr=str(model.ip_or_cidr),
        category=model.category,
        confidence=model.confidence
    )
    try:
        db.add(row); db.commit()
    except OperationalError as e:
        if "no such table" in str(e).lower():
            import app.models  # ensure models are registered
            Base.metadata.create_all(bind=engine)
            db.add(row); db.commit()
        else:
            raise
    except IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            # Rollback the session first
            db.rollback()
            # Update existing record instead
            existing = db.query(Indicator).filter(Indicator.ip_or_cidr == str(model.ip_or_cidr)).first()
            if existing:
                existing.category = model.category
                existing.confidence = model.confidence
                db.commit()
            else:
                raise
        else:
            raise

def remove_indicator(db: Session, ip_or_cidr: str):
    try:
        db.query(Indicator).filter(Indicator.ip_or_cidr == ip_or_cidr).delete()
        db.commit()
    except OperationalError as e:
        if "no such table" in str(e).lower():
            import app.models
            Base.metadata.create_all(bind=engine)
            # If table was missing, nothing to delete; treat as success
            return
        else:
            raise

def get_indicator(indicator_id: str) -> Optional[Dict[str, Any]]:
    """Get a threat intelligence indicator by ID"""
    return _indicators.get(indicator_id)

def list_indicators() -> List[Dict[str, Any]]:
    """List all threat intelligence indicators"""
    return list(_indicators.values())
