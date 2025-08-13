import os
import ipaddress
from typing import List, Dict, Any
from pathlib import Path

class ThreatIntel:
    def __init__(self):
        self.ti_path = os.getenv("TI_PATH", "/data/ti/indicators.txt")
        self.enable_ti = os.getenv("ENRICH_ENABLE_TI", "true").lower() == "true"
        self.cidr_networks = []
        self.domains = set()
        self._load_indicators()
        
    def _load_indicators(self):
        """Load threat indicators from plain text file"""
        if not self.enable_ti:
            return
            
        try:
            path = Path(self.ti_path)
            if not path.exists():
                print(f"Warning: Threat intelligence file not found: {self.ti_path}")
                return
                
            with open(path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    # Handle domain indicators
                    if line.startswith('domain:'):
                        domain = line[7:].strip()
                        if domain:
                            self.domains.add(domain)
                        continue
                        
                    # Handle CIDR indicators
                    try:
                        network = ipaddress.ip_network(line, strict=False)
                        self.cidr_networks.append(network)
                    except ValueError:
                        # Try as single IP
                        try:
                            ip = ipaddress.ip_address(line)
                            network = ipaddress.ip_network(f"{ip}/32", strict=False)
                            self.cidr_networks.append(network)
                        except ValueError:
                            print(f"Warning: Invalid indicator on line {line_num}: {line}")
                            
            print(f"Loaded {len(self.cidr_networks)} CIDR networks and {len(self.domains)} domains")
            
        except Exception as e:
            print(f"Error loading threat indicators: {e}")
            
    def match_ip(self, ip: str) -> List[str]:
        """Match IP against threat indicators"""
        if not ip or not self.enable_ti:
            return []
            
        matches = []
        try:
            ip_addr = ipaddress.ip_address(ip)
            for network in self.cidr_networks:
                if ip_addr in network:
                    matches.append(str(network))
        except ValueError:
            pass
            
        return matches
        
    def match_domain(self, domain: str) -> List[str]:
        """Match domain against threat indicators"""
        if not domain or not self.enable_ti:
            return []
            
        matches = []
        if domain in self.domains:
            matches.append(domain)
            
        return matches

# Global instance
threat_intel = ThreatIntel()

def match_ip(ip: str) -> List[str]:
    """Convenience function to match IP against threat indicators"""
    return threat_intel.match_ip(ip)

def match_domain(domain: str) -> List[str]:
    """Convenience function to match domain against threat indicators"""
    return threat_intel.match_domain(domain)
