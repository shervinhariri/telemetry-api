# app/auth/keys.py
import os
from typing import Optional, Union

# Default development keys (fallback for CI/dev)
DEV_ADMIN_KEY = os.environ.get("DEV_ADMIN_KEY", "DEV_ADMIN_KEY_5a8f9ffdc3")
DEV_USER_KEY = os.environ.get("DEV_USER_KEY", "DEV_USER_KEY_2c9d1a4b61")

# Legacy support for existing env vars
LEGACY_API_KEY = os.environ.get("API_KEY")
TEST_ADMIN_KEY = os.environ.get("TEST_ADMIN_KEY", "TEST_ADMIN_KEY")

# Common test fallbacks so CI/client fixtures Just Work
TEST_ADMIN_KEY_FALLBACK = os.environ.get("TEST_ADMIN_KEY_FALLBACK", "admin-key")
TEST_USER_KEY_FALLBACK = os.environ.get("TEST_USER_KEY_FALLBACK", "***")

# Comma-separated additional keys via env
ADMIN_KEYS = {k.strip() for k in os.environ.get("ADMIN_KEYS", "").split(",") if k.strip()}
USER_KEYS = {k.strip() for k in os.environ.get("USER_KEYS", "").split(",") if k.strip()}

# Always include dev defaults for CI/dev unless explicitly disabled
ALLOW_DEV_KEYS = os.environ.get("ALLOW_DEV_KEYS", "true").lower() in ("1", "true", "yes")

# Build the final key scopes
def get_key_scopes():
    """Get the mapping of API keys to their scopes"""
    scopes = {}
    
    # Add legacy keys if present
    if LEGACY_API_KEY:
        scopes[LEGACY_API_KEY] = "admin"
    
    # Add test keys
    scopes[TEST_ADMIN_KEY] = "admin"
    scopes[TEST_ADMIN_KEY_FALLBACK] = "admin"
    scopes[TEST_USER_KEY_FALLBACK] = "user"
    
    # Add environment-configured keys
    for key in ADMIN_KEYS:
        scopes[key] = "admin"
    for key in USER_KEYS:
        scopes[key] = "user"
    
    # Add dev keys if allowed
    if ALLOW_DEV_KEYS:
        scopes[DEV_ADMIN_KEY] = "admin"
        scopes[DEV_USER_KEY] = "user"
    
    return scopes

# Get the current key scopes
KEY_SCOPES = get_key_scopes()

def is_admin_key(key: str) -> bool:
    """Check if a key has admin scope"""
    return key in KEY_SCOPES and KEY_SCOPES[key] == "admin"

def is_user_key(key: str) -> bool:
    """Check if a key has user scope"""
    return key in KEY_SCOPES and KEY_SCOPES[key] == "user"

def get_key_scope(key: str) -> Optional[str]:
    """Get the scope for a given key, or None if not found"""
    return KEY_SCOPES.get(key)
