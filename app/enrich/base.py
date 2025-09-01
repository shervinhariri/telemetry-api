"""
Base enrichment loader class
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger("enrich.base")

class EnrichmentLoader(ABC):
    """Base class for enrichment loaders"""
    
    def __init__(self, name: str):
        self.name = name
        self.loaded = False
        self.last_refresh = 0
        self.error_count = 0
        
    @abstractmethod
    def load(self) -> bool:
        """Load the enrichment data"""
        pass
    
    @abstractmethod
    def lookup(self, key: str) -> Optional[Dict[str, Any]]:
        """Lookup enrichment data for a key"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get loader status"""
        return {
            "status": "loaded" if self.loaded else "missing",
            "last_refresh": self.last_refresh,
            "error_count": self.error_count
        }
    
    def refresh(self) -> bool:
        """Refresh the enrichment data"""
        return self.load()
