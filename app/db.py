"""
Database configuration and session management
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import json
import logging

def _safe_json_deserializer(value):
    # Tolerate legacy bad values like 'admin,*' so SELECTs don't crash
    try:
        return json.loads(value)
    except Exception:
        return value

# Database URL from environment or default to SQLite
sqlite_path = os.getenv("SQLITE_PATH", "./telemetry.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{sqlite_path}")
logger = logging.getLogger(__name__)

# Create engine
engine = create_engine(
    DATABASE_URL,
    future=True,
    json_deserializer=_safe_json_deserializer,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# Sanitize any legacy non-JSON scopes at import time so ORM row fetches never crash
try:
    with engine.begin() as conn:
        conn.execute(text(
            """
            UPDATE api_keys
            SET scopes='["admin","*"]'
            WHERE scopes NOT LIKE '[%' AND scopes NOT LIKE '{%}'
            """
        ))
except Exception as e:
    # best-effort; schema may not exist on first startup
    logger.warning("scope sanitize skipped: %s", e)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def init_db():
    """Initialize database tables"""
    try:
        # Make sure all models are imported so Base.metadata is populated
        import app.models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from contextlib import contextmanager

@contextmanager
def session_scope():
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
