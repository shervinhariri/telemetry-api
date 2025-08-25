"""
Configuration module for Telemetry API
"""

# Application configuration
import os

def env_bool(key: str, default: bool = False) -> bool:
    """Get boolean value from environment variable"""
    value = os.getenv(key, str(default)).lower()
    return value in ("true", "1", "yes", "on")

# Version information
from pathlib import Path

def _read_version_from_repo(default: str = "dev") -> str:
    try:
        # repo root: app/.. (two parents up)
        version_file = Path(__file__).resolve().parents[2] / "VERSION"
        v = version_file.read_text(encoding="utf-8").strip()
        if v:
            return v
    except Exception:
        pass
    return os.getenv("APP_VERSION", default)

API_VERSION = _read_version_from_repo()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./telemetry.db")

# API configuration
API_KEY = os.getenv("API_KEY", "TEST_KEY")
APP_PORT = int(os.getenv("APP_PORT", "80"))

# GeoIP configuration
GEOIP_DB_CITY = os.getenv("GEOIP_DB_CITY", "/data/geo/GeoLite2-City.mmdb")
GEOIP_DB_ASN = os.getenv("GEOIP_DB_ASN", "/data/geo/GeoLite2-ASN.mmdb")

# Threat intelligence configuration
THREATLIST_CSV = os.getenv("THREATLIST_CSV", "/data/ti/indicators.txt")

# Demo configuration
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
DEMO_EPS = int(os.getenv("DEMO_EPS", "50"))
DEMO_DURATION_SEC = int(os.getenv("DEMO_DURATION_SEC", "120"))
DEMO_VARIANTS = os.getenv("DEMO_VARIANTS", "netflow,zeek").split(",")

# Logging configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "text")
HTTP_LOG_ENABLED = os.getenv("HTTP_LOG_ENABLED", "true").lower() == "true"
HTTP_LOG_SAMPLE_RATE = float(os.getenv("HTTP_LOG_SAMPLE_RATE", "0.1"))
HTTP_LOG_EXCLUDE_PATHS = set(os.getenv("HTTP_LOG_EXCLUDE_PATHS", "/v1/metrics,/v1/system,/v1/logs/tail,/v1/admin/requests").split(","))

# Security configuration
REDACT_HEADERS = os.getenv("REDACT_HEADERS", "authorization,x-api-key").split(",")
REDACT_FIELDS = os.getenv("REDACT_FIELDS", "password,token").split(",")

# Admission control configuration
ADMISSION_HTTP_ENABLED: bool = env_bool("ADMISSION_HTTP_ENABLED", False)
ADMISSION_UDP_ENABLED: bool = env_bool("ADMISSION_UDP_ENABLED", False)
HTTP_IP_ALLOWLIST_ENABLED: bool = env_bool("HTTP_IP_ALLOWLIST_ENABLED", False)
HTTP_TRUST_XFF: bool = env_bool("HTTP_TRUST_XFF", True)
ADMISSION_LOG_ONLY: bool = env_bool("ADMISSION_LOG_ONLY", False)  # block→log-only
ADMISSION_FAIL_OPEN: bool = env_bool("ADMISSION_FAIL_OPEN", False)  # on internal errors, allow
ADMISSION_COMPAT_ALLOW_EMPTY_IPS: bool = env_bool("ADMISSION_COMPAT_ALLOW_EMPTY_IPS", False)  # [] means allow-any (legacy)
ADMISSION_BLOCK_ON_EXCEED_DEFAULT: bool = env_bool("ADMISSION_BLOCK_ON_EXCEED_DEFAULT", True)

TRUST_PROXY: bool = env_bool("TRUST_PROXY", False)

# Admin configuration
ADMIN_AUDIT_MAX = int(os.getenv("ADMIN_AUDIT_MAX", "1000"))
ADMIN_AUDIT_TTL_MINUTES = int(os.getenv("ADMIN_AUDIT_TTL_MINUTES", "60"))
ADMIN_SHOW_LOG_TAIL = os.getenv("ADMIN_SHOW_LOG_TAIL", "false").lower() == "true"

# Export configuration
EXPORT_ELASTIC_ENABLED = os.getenv("EXPORT_ELASTIC_ENABLED", "false").lower() == "true"
EXPORT_SPLUNK_ENABLED = os.getenv("EXPORT_SPLUNK_ENABLED", "false").lower() == "true"

# Enrichment configuration
ENRICH_ENABLE_GEOIP = os.getenv("ENRICH_ENABLE_GEOIP", "true").lower() == "true"
ENRICH_ENABLE_ASN = os.getenv("ENRICH_ENABLE_ASN", "true").lower() == "true"
ENRICH_ENABLE_TI = os.getenv("ENRICH_ENABLE_TI", "true").lower() == "true"

# API configuration
API_PREFIX = "/v1"

# Output configurations
SPLUNK_HEC_URL = os.getenv("SPLUNK_HEC_URL", "")
SPLUNK_HEC_TOKEN = os.getenv("SPLUNK_HEC_TOKEN", "")
ELASTIC_URL = os.getenv("ELASTIC_URL", "")
ELASTIC_USERNAME = os.getenv("ELASTIC_USERNAME", "")
ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD", "")

# Logging configuration
LOG_FILE = os.getenv("LOG_FILE", "/app/data/logs/app.log")

# Retention configuration
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "7"))

# Runtime configuration manager for feature flags
class RuntimeConfig:
    """Runtime configuration manager for feature flags"""
    
    def __init__(self):
        self._flags = {}
        self._load_from_env()
    
    def _load_from_env(self):
        """Load flags from environment variables"""
        self._flags = {
            "ADMISSION_HTTP_ENABLED": env_bool("ADMISSION_HTTP_ENABLED", False),
            "ADMISSION_UDP_ENABLED": env_bool("ADMISSION_UDP_ENABLED", False),
            "HTTP_IP_ALLOWLIST_ENABLED": env_bool("HTTP_IP_ALLOWLIST_ENABLED", False),
            "HTTP_TRUST_XFF": env_bool("HTTP_TRUST_XFF", True),
            "ADMISSION_LOG_ONLY": env_bool("ADMISSION_LOG_ONLY", False),
            "ADMISSION_FAIL_OPEN": env_bool("ADMISSION_FAIL_OPEN", False),
            "ADMISSION_COMPAT_ALLOW_EMPTY_IPS": env_bool("ADMISSION_COMPAT_ALLOW_EMPTY_IPS", False),
            "ADMISSION_BLOCK_ON_EXCEED_DEFAULT": env_bool("ADMISSION_BLOCK_ON_EXCEED_DEFAULT", True),
            "TRUST_PROXY": env_bool("TRUST_PROXY", False),
        }
    
    def get(self, key: str, default=None):
        """Get a flag value"""
        return self._flags.get(key, default)
    
    def set(self, key: str, value: bool):
        """Set a flag value"""
        if key in self._flags:
            self._flags[key] = bool(value)
    
    def update(self, updates: dict):
        """Update multiple flags"""
        for key, value in updates.items():
            if key in self._flags:
                self._flags[key] = bool(value)
    
    def get_all(self) -> dict:
        """Get all flags"""
        return self._flags.copy()

# Global runtime config instance
runtime_config = RuntimeConfig()

# Queue and worker configuration
QUEUE_MAX_DEPTH = int(os.getenv("QUEUE_MAX_DEPTH", "10000"))
WORKER_POOL_SIZE = int(os.getenv("WORKER_POOL_SIZE", "4"))
QUEUE_RETRY_AFTER_SECONDS = int(os.getenv("QUEUE_RETRY_AFTER_SECONDS", "2"))
ENRICH_TIMEOUT_MS = int(os.getenv("ENRICH_TIMEOUT_MS", "500"))
DISPATCH_TIMEOUT_MS = int(os.getenv("DISPATCH_TIMEOUT_MS", "1000"))

# Feature flags
FEATURES = {
    "sources": env_bool("FEATURE_SOURCES", True),
    "udp_head": env_bool("FEATURE_UDP_HEAD", False)
}

# Feature flag accessors
def get_admission_http_enabled() -> bool:
    return runtime_config.get("ADMISSION_HTTP_ENABLED", False)

def get_admission_udp_enabled() -> bool:
    return runtime_config.get("ADMISSION_UDP_ENABLED", False)

def get_admission_log_only() -> bool:
    return runtime_config.get("ADMISSION_LOG_ONLY", False)

def get_admission_fail_open() -> bool:
    return runtime_config.get("ADMISSION_FAIL_OPEN", False)

def get_admission_compat_allow_empty_ips() -> bool:
    return runtime_config.get("ADMISSION_COMPAT_ALLOW_EMPTY_IPS", False)

def get_admission_block_on_exceed_default() -> bool:
    return runtime_config.get("ADMISSION_BLOCK_ON_EXCEED_DEFAULT", True)

def get_trust_proxy() -> bool:
    return runtime_config.get("TRUST_PROXY", False)

def get_http_ip_allowlist_enabled() -> bool:
    """Get HTTP IP allow-list enabled flag"""
    return runtime_config.get("HTTP_IP_ALLOWLIST_ENABLED", False)

def get_http_trust_xff() -> bool:
    """Get HTTP trust X-Forwarded-For flag"""
    return runtime_config.get("HTTP_TRUST_XFF", True)
