"""
Risk scoring module
Calculates risk scores based on threat intelligence matches and other factors
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("enrich.risk")

def score(record: Dict[str, Any], ti_matches: List[Dict[str, Any]]) -> int:
    """Calculate risk score for a record"""
    score = 0
    
    # Base score from threat intelligence matches
    for match in ti_matches:
        if match.get("type") == "ip":
            score += 50  # IP match
        elif match.get("type") == "domain":
            score += 30  # Domain match
    
    # Additional risk factors
    if _is_suspicious_port(record):
        score += 20
    
    if _is_suspicious_protocol(record):
        score += 15
    
    if _is_high_volume(record):
        score += 10
    
    # Cap score at 100
    return min(score, 100)

def _is_suspicious_port(record: Dict[str, Any]) -> bool:
    """Check if record involves suspicious ports"""
    suspicious_ports = {22, 23, 3389, 445, 1433, 3306, 5432}  # SSH, Telnet, RDP, etc.
    
    src_port = record.get('src_port') or record.get('id_orig_p')
    dst_port = record.get('dst_port') or record.get('id_resp_p')
    
    return (src_port in suspicious_ports or dst_port in suspicious_ports)

def _is_suspicious_protocol(record: Dict[str, Any]) -> bool:
    """Check if record involves suspicious protocols"""
    protocol = record.get('proto') or record.get('protocol', '').lower()
    suspicious_protocols = {'telnet', 'ftp', 'smtp'}
    
    return protocol in suspicious_protocols

def _is_high_volume(record: Dict[str, Any]) -> bool:
    """Check if record has high data volume"""
    bytes_transferred = record.get('bytes') or record.get('bytes_out', 0)
    packets = record.get('packets', 0)
    
    # High volume thresholds
    return bytes_transferred > 1000000 or packets > 1000
