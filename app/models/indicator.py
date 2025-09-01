from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from ..db import Base

class Indicator(Base):
    __tablename__ = "indicators"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_or_cidr = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, nullable=False)
    confidence = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
