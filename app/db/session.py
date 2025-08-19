import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Default to SQLite; allow override via env for Postgres (or any SQLAlchemy URL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./telemetry.db")

# SQLite needs special connect args; Postgres does not
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


