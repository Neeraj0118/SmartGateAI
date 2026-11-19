"""
Database engine configuration and session management for SmartGateAI.
Ensures SQLite enforces foreign keys and supports concurrent reads.
"""

import os
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from .base import Base


# Default database location inside storage directory
DEFAULT_DB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "storage"
)
os.makedirs(DEFAULT_DB_DIR, exist_ok=True)
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "smartgate.db")
DEFAULT_DB_URL = f"sqlite:///{DEFAULT_DB_PATH}"


def get_engine(db_url: str = DEFAULT_DB_URL) -> Engine:
    """Create and configure the SQLAlchemy engine."""
    connect_args = {}
    if db_url.startswith("sqlite"):
        # check_same_thread=False allows FastAPI / worker threads to share connection objects
        connect_args["check_same_thread"] = False

    engine = create_engine(
        db_url,
        connect_args=connect_args,
        echo=False
    )

    # Enable foreign key constraint enforcement in SQLite
    if db_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


# Default engine & sessionmaker instance
engine = get_engine(DEFAULT_DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(target_engine: Engine = engine) -> None:
    """Create all registered tables if they do not exist."""
    # Ensure all models are imported before creating tables
    from ..models.student import Student, FaceEmbedding  # noqa: F401
    Base.metadata.create_all(bind=target_engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency / context manager yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
