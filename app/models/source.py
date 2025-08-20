from sqlalchemy import Column, String, DateTime, Index, Text, Integer, Boolean
from sqlalchemy.sql import func
from app.db import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    type = Column(String, nullable=False)  # cisco_asa, cisco_ftd, palo_alto, aws_vpc, etc.
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
        }
