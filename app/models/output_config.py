from sqlalchemy import Column, String, Boolean, JSON, ForeignKey, Integer
from app.db import Base

class OutputConfig(Base):
    __tablename__ = "output_configs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), ForeignKey("tenants.tenant_id"), index=True, nullable=False)
    type = Column(String(32), nullable=False)  # "splunk" | "elastic"
    config = Column(JSON, nullable=False, default={})
    enabled = Column(Boolean, nullable=False, default=False)
