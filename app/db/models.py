from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Integer, Float, JSON, Boolean, DateTime, Index

Base = declarative_base()


class Event(Base):
    __tablename__ = "events"
    id = Column(String, primary_key=True)
    tenant_id = Column(String, index=True, nullable=False)
    ts = Column(Float, index=True)
    src_ip = Column(String, index=True)
    dst_ip = Column(String, index=True)
    risk = Column(Integer, index=True)
    payload = Column(JSON)

    __table_args__ = (
        Index("ix_events_tenant_ts", "tenant_id", "ts"),
    )


class RequestsAudit(Base):
    __tablename__ = "requests_audit"
    id = Column(String, primary_key=True)
    tenant_id = Column(String, index=True, nullable=False)
    path = Column(String, index=True)
    method = Column(String, index=True)
    status = Column(Integer, index=True)
    latency_ms = Column(Integer)
    ts = Column(DateTime, index=True)


class OutputConfig(Base):
    __tablename__ = "outputs"
    id = Column(String, primary_key=True)
    tenant_id = Column(String, index=True, nullable=False)
    kind = Column(String, index=True)
    config = Column(JSON)
    enabled = Column(Boolean, default=True)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    key = Column(String, primary_key=True)
    tenant_id = Column(String, index=True, nullable=False)
    ts = Column(DateTime, index=True)


