"""
Configuration module for Telemetry API
"""

import os

# Demo Mode Configuration
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
DEMO_EPS = int(os.getenv("DEMO_EPS", "50"))
DEMO_DURATION_SEC = int(os.getenv("DEMO_DURATION_SEC", "120"))
DEMO_VARIANTS = os.getenv("DEMO_VARIANTS", "netflow,zeek").split(",")

# API Configuration
API_PREFIX = "/v1"
API_KEY = os.getenv("API_KEY", "TEST_KEY")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./telemetry.db")

# GeoIP Configuration
GEOIP_DB_CITY = os.getenv("GEOIP_DB_CITY", "/data/GeoLite2-City.mmdb")
GEOIP_DB_ASN = os.getenv("GEOIP_DB_ASN", "/data/GeoLite2-ASN.mmdb")

# Threat Intelligence Configuration
THREATLIST_CSV = os.getenv("THREATLIST_CSV", "/data/threats.csv")

# Output configurations
SPLUNK_HEC_URL = os.getenv("SPLUNK_HEC_URL", "")
SPLUNK_HEC_TOKEN = os.getenv("SPLUNK_HEC_TOKEN", "")
ELASTIC_URL = os.getenv("ELASTIC_URL", "")
ELASTIC_USERNAME = os.getenv("ELASTIC_USERNAME", "")
ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD", "")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "/app/data/logs/app.log")

# Retention Configuration
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "7"))
