"""
Admin Audit Log Model
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from ..db import Base


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    actor_key_id = Column(String(255), nullable=False, index=True)  # API key ID that performed the action
    action = Column(String(100), nullable=False, index=True)  # e.g., "feature_flag_update", "source_update", "firewall_sync"
    target = Column(String(255), nullable=False)  # Target of the action (e.g., "ADMISSION_HTTP_ENABLED", "source:src_123")
    before_value = Column(Text, nullable=True)  # JSON of previous state
    after_value = Column(Text, nullable=True)   # JSON of new state
    client_ip = Column(String(45), nullable=True)  # IPv4/IPv6 address
    user_agent = Column(String(500), nullable=True)  # User agent string
