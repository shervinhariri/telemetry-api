import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Default to SQLite; allow override via env for Postgres (or any SQLAlchemy URL)
sqlite_path = os.getenv("SQLITE_PATH", "./telemetry.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{sqlite_path}")

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


