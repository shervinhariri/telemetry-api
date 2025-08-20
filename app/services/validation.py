"""
Validation utilities for security and data integrity
"""

import ipaddress
import re
from typing import List, Dict, Any, Tuple


def validate_cidr_list(cidrs: List[str], max_count: int = 128) -> Tuple[bool, str]:
    """
    Validate a list of CIDR strings
    
    Args:
        cidrs: List of CIDR strings to validate
        max_count: Maximum number of CIDRs allowed
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    
    if len(cidrs) > max_count:
        return False, f"Too many CIDRs: {len(cidrs)} (max: {max_count})"
    
    for i, cidr in enumerate(cidrs):
        if not validate_cidr(cidr):
            return False, f"Invalid CIDR at index {i}: '{cidr}'"
    
    return True, ""


def validate_cidr(cidr: str) -> bool:
    """
    Validate a single CIDR string
    
    Args:
        cidr: CIDR string to validate (e.g., "192.168.1.0/24")
        
    Returns:
        True if valid, False otherwise
    """
    
    if not cidr or not isinstance(cidr, str):
        return False
        
    try:
        # This will raise ValueError if invalid
        network = ipaddress.ip_network(cidr, strict=False)
        
        # Additional checks
        if network.is_loopback and not str(network).startswith(('127.', '::1')):
            return False
            
        return True
        
    except (ValueError, TypeError):
        return False


def validate_source_limits(source_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate source limits and constraints
    
    Args:
        source_data: Source data dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    
    # Validate allowed_ips
    allowed_ips = source_data.get('allowed_ips', [])
    if isinstance(allowed_ips, str):
        import json
        try:
            allowed_ips = json.loads(allowed_ips)
        except json.JSONDecodeError:
            return False, "Invalid allowed_ips JSON format"
    
    if allowed_ips:
        is_valid, error = validate_cidr_list(allowed_ips, max_count=128)
        if not is_valid:
            return False, f"allowed_ips validation failed: {error}"
    
    # Validate max_eps
    max_eps = source_data.get('max_eps', 0)
    if not isinstance(max_eps, int) or max_eps < 0:
        return False, "max_eps must be a non-negative integer"
    
    if max_eps > 1000000:  # 1M EPS limit
        return False, "max_eps cannot exceed 1,000,000"
    
    # Validate block_on_exceed
    block_on_exceed = source_data.get('block_on_exceed', True)
    if not isinstance(block_on_exceed, bool):
        return False, "block_on_exceed must be a boolean"
    
    return True, ""


def validate_global_cidr_limits(all_sources: List[Dict[str, Any]], max_total: int = 2048) -> Tuple[bool, str]:
    """
    Validate global CIDR limits across all sources
    
    Args:
        all_sources: List of all source dictionaries
        max_total: Maximum total CIDRs across all sources
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    
    total_cidrs = 0
    unique_cidrs = set()
    
    for source in all_sources:
        allowed_ips = source.get('allowed_ips', [])
        if isinstance(allowed_ips, str):
            import json
            try:
                allowed_ips = json.loads(allowed_ips)
            except json.JSONDecodeError:
                continue
        
        for cidr in allowed_ips:
            total_cidrs += 1
            unique_cidrs.add(cidr)
    
    if total_cidrs > max_total:
        return False, f"Total CIDRs across all sources ({total_cidrs}) exceeds limit ({max_total})"
    
    return True, ""
