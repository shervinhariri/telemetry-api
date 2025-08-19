"""
Configuration module for Telemetry API
"""

# Application configuration
import os

# Version information
API_VERSION = "0.8.3"

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
