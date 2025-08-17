"""
API Key Management with Scopes and Rotation
"""
import hashlib
import time
import json
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import logging

# In-memory storage for API keys (in production, use database)
API_KEYS: Dict[str, Dict] = {}
KEY_HASHES: Dict[str, str] = {}

# Default scopes
SCOPES = {
    "ingest": "Ingest data (zeek, netflow, bulk)",
    "manage_indicators": "Manage threat intelligence indicators", 
    "export": "Export data to external systems",
    "read_requests": "Read request audit logs",
    "read_metrics": "Read system metrics",
    "admin": "Full administrative access"
}

def hash_api_key(api_key: str) -> str:
    """Hash API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()

def create_api_key(scopes: List[str], note: str = "", created_by: str = "system") -> Dict[str, str]:
    """Create a new API key with specified scopes"""
    # Generate key ID and secret
    key_id = hashlib.md5(f"{time.time()}:{note}".encode()).hexdigest()[:8]
    key_secret = hashlib.md5(f"{time.time()}:{key_id}:{scopes}".encode()).hexdigest()[:16]
    full_key = f"{key_id}.{key_secret}"
    
    # Hash the full key for storage
    key_hash = hash_api_key(full_key)
    
    # Store key metadata
    API_KEYS[key_id] = {
        "scopes": set(scopes),
        "note": note,
        "created_by": created_by,
        "created_at": time.time(),
        "last_used_at": None,
        "is_active": True
    }
    
    # Store hash for validation
    KEY_HASHES[key_hash] = key_id
    
    logging.info(f"Created API key {key_id} with scopes: {scopes}")
    
    return {
        "key_id": key_id,
        "api_key": full_key,
        "scopes": scopes,
        "note": note,
        "created_at": datetime.fromtimestamp(time.time()).isoformat()
    }

def require_api_key(auth_header: Optional[str], required_scopes: Optional[List[str]] = None) -> Dict:
    """Require API key with optional scope validation - raises HTTPException on failure"""
    from fastapi import HTTPException
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    api_key = auth_header.split(" ", 1)[1].strip()
    key_data = validate_api_key(api_key, required_scopes)
    
    if not key_data:
        raise HTTPException(status_code=403, detail="Invalid API key or insufficient permissions")
    
    return key_data

def validate_api_key(api_key: str, required_scopes: Optional[List[str]] = None) -> Optional[Dict]:
    """Validate API key and check scopes"""
    if not api_key:
        return None
    
    # Try legacy API key first
    legacy_result = validate_legacy_api_key(api_key)
    if legacy_result:
        # Check scopes for legacy key
        if required_scopes:
            legacy_scopes = legacy_result.get("scopes", [])
            # Admin scope grants access to all scopes
            if "admin" not in legacy_scopes and not all(scope in legacy_scopes for scope in required_scopes):
                logging.warning(f"Legacy API key lacks required scopes: {required_scopes}")
                return None
        return legacy_result
    
    # Hash the provided key
    key_hash = hash_api_key(api_key)
    
    # Find key ID
    key_id = KEY_HASHES.get(key_hash)
    if not key_id:
        return None
    
    # Get key metadata
    key_data = API_KEYS.get(key_id)
    if not key_data or not key_data.get("is_active"):
        return None
    
    # Update last used timestamp
    key_data["last_used_at"] = time.time()
    
    # Check scopes if required
    if required_scopes:
        key_scopes = key_data.get("scopes", set())
        # Admin scope grants access to all scopes
        if "admin" not in key_scopes and not all(scope in key_scopes for scope in required_scopes):
            logging.warning(f"API key {key_id} lacks required scopes: {required_scopes}")
            return None
    
    return {
        "key_id": key_id,
        "scopes": list(key_data.get("scopes", set())),
        "note": key_data.get("note", ""),
        "created_at": key_data.get("created_at"),
        "last_used_at": key_data.get("last_used_at")
    }

def delete_api_key(key_id: str) -> bool:
    """Delete an API key"""
    if key_id not in API_KEYS:
        return False
    
    # Remove from storage
    key_data = API_KEYS.pop(key_id)
    
    # Remove hash (we'd need to store the original key to do this properly)
    # For now, we'll just mark as inactive
    key_data["is_active"] = False
    
    logging.info(f"Deleted API key {key_id}")
    return True

def list_api_keys() -> List[Dict]:
    """List all API keys (without secrets)"""
    keys = []
    for key_id, key_data in API_KEYS.items():
        keys.append({
            "key_id": key_id,
            "scopes": list(key_data.get("scopes", set())),
            "note": key_data.get("note", ""),
            "created_by": key_data.get("created_by", ""),
            "created_at": datetime.fromtimestamp(key_data.get("created_at", 0)).isoformat(),
            "last_used_at": datetime.fromtimestamp(key_data.get("last_used_at", 0)).isoformat() if key_data.get("last_used_at") else None,
            "is_active": key_data.get("is_active", True)
        })
    return keys

def rotate_api_key(key_id: str) -> Optional[Dict[str, str]]:
    """Rotate an existing API key"""
    if key_id not in API_KEYS:
        return None
    
    key_data = API_KEYS[key_id]
    
    # Generate new secret
    key_secret = hashlib.md5(f"{time.time()}:{key_id}:rotate".encode()).hexdigest()[:16]
    new_full_key = f"{key_id}.{key_secret}"
    
    # Update hash
    new_hash = hash_api_key(new_full_key)
    KEY_HASHES[new_hash] = key_id
    
    # Update metadata
    key_data["last_used_at"] = time.time()
    
    logging.info(f"Rotated API key {key_id}")
    
    return {
        "key_id": key_id,
        "api_key": new_full_key,
        "scopes": list(key_data.get("scopes", set())),
        "note": key_data.get("note", ""),
        "rotated_at": datetime.fromtimestamp(time.time()).isoformat()
    }

def get_available_scopes() -> Dict[str, str]:
    """Get available scopes with descriptions"""
    return SCOPES.copy()

# Initialize with default key if none exist
def initialize_default_keys():
    """Initialize default API keys if none exist"""
    if not API_KEYS:
        # Create default admin key
        create_api_key(
            scopes=["admin"],
            note="Default admin key",
            created_by="system"
        )
        
        # Create default ingest key
        create_api_key(
            scopes=["ingest", "read_metrics"],
            note="Default ingest key",
            created_by="system"
        )
        
        logging.info("Initialized default API keys")

def validate_legacy_api_key(api_key: str) -> Optional[Dict]:
    """Validate legacy API key for backward compatibility"""
    # Import here to avoid circular imports
    import os
    legacy_key = os.getenv("API_KEY", "TEST_KEY")
    
    if api_key == legacy_key:
        return {
            "key_id": "legacy",
            "scopes": ["admin"],  # Legacy keys have full access
            "note": "Legacy API key",
            "created_at": None,
            "last_used_at": None
        }
    return None

# Initialize on module load
initialize_default_keys()
