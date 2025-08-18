from sqlalchemy import Column, String, Integer, JSON, DateTime, func
from app.db import Base

class Tenant(Base):
    __tablename__ = "tenants"
    tenant_id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    retention_days = Column(Integer, nullable=False, default=7)  # Step-1 default
    quotas = Column(JSON, nullable=False, default={"eps": 600, "batch_max": 10000, "dlq_max": 100000})
    redaction = Column(JSON, nullable=False, default={"fields": []})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
