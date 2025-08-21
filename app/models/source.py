import time
from sqlalchemy import Column, String, DateTime, Index, Text, Integer, Boolean, Float
from sqlalchemy.sql import func
from app.db import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "udp" | "http" (future: "syslog") - declared intent
    origin = Column(String, nullable=True)  # "udp" | "http" | "unknown" - actual traffic origin
    display_name = Column(String, nullable=False)
    collector = Column(String, nullable=False)  # e.g. gw-local
    site = Column(String)  # Krakow, HQ, ...
    tags = Column(Text)  # JSON array string: ["branch","prod"]
    health_status = Column(String, default="stale")  # healthy|degraded|stale
    last_seen = Column(DateTime)
    notes = Column(Text)
    # Security fields
    status = Column(String, nullable=False, default="enabled")  # "enabled" | "disabled"
    allowed_ips = Column(Text, nullable=False, default="[]")  # JSON array of CIDR strings
    max_eps = Column(Integer, nullable=False, default=0)  # 0 = unlimited
    block_on_exceed = Column(Boolean, nullable=False, default=True)
    
    # New fields for source typing and stats
    enabled = Column(Boolean, nullable=False, default=True)
    eps_cap = Column(Integer, nullable=False, default=0)  # 0 = unlimited
    last_seen_ts = Column(Integer, nullable=True)  # Unix timestamp
    eps_1m = Column(Float, nullable=True)  # computed rolling EPS
    error_pct_1m = Column(Float, nullable=True)  # computed rolling error %
    created_at = Column(Integer, nullable=False)  # Unix timestamp
    updated_at = Column(Integer, nullable=False)  # Unix timestamp

    # Indexes for performance
    __table_args__ = (
        Index("idx_sources_tenant", "tenant_id"),
        Index("idx_sources_health_status", "health_status"),
        Index("idx_sources_status", "status"),
        Index("idx_sources_last_seen", "last_seen"),
    )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "type": self.type,
            "origin": self.origin,
            "display_name": self.display_name,
            "collector": self.collector,
            "site": self.site,
            "tags": self.tags,
            "health_status": self.health_status,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "notes": self.notes,
            "status": self.status,
            "allowed_ips": self.allowed_ips,
            "max_eps": self.max_eps,
            "block_on_exceed": self.block_on_exceed,
            # New fields
            "enabled": self.enabled,
            "eps_cap": self.eps_cap,
            "last_seen_ts": self.last_seen_ts,
            "eps_1m": self.eps_1m,
            "error_pct_1m": self.error_pct_1m,
            "created_at": self.created_at or int(time.time()),
            "updated_at": self.updated_at or int(time.time()),
        }
