from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text, func
from app.db import Base

class Job(Base):
    __tablename__ = "jobs"
    job_id = Column(String(36), primary_key=True)  # uuid4
    tenant_id = Column(String(64), ForeignKey("tenants.tenant_id"), index=True, nullable=False)
    type = Column(String(64), nullable=False)
    args = Column(JSON, nullable=False, default={})
    status = Column(String(16), nullable=False, default="queued")  # queued|running|success|error
    logs = Column(Text, nullable=False, default="")
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
