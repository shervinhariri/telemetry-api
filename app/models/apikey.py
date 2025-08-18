from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, func
from app.db import Base

class ApiKey(Base):
    __tablename__ = "api_keys"
    key_id = Column(String(32), primary_key=True)
    tenant_id = Column(String(64), ForeignKey("tenants.tenant_id"), index=True, nullable=False)
    hash = Column(String(128), nullable=False)           # hashed secret
    scopes = Column(JSON, nullable=False, default=["ingest"])
    disabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
