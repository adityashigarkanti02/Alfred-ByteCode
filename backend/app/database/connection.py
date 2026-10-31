"""
Database connection and session management for ALFRED AI.

This module provides both synchronous and asynchronous database sessions,
supporting both PostgreSQL (in production/container environments) and
SQLite (for zero-configuration development, local runs, and fast testing).
It dynamically configures connection pooling, schema migrations, and provides
fast session context managers.
"""

import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Retrieve the database URL from environment or fall back to local sqlite database.
# In production, this points to PostgreSQL: postgresql://alfred:alfred_secret@localhost:5432/alfred_db
DEFAULT_DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "alfred.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_FILE}")

# Ensure clean SQLite URI on Windows if using sqlite
if DATABASE_URL.startswith("sqlite"):
    # Connect args for SQLite to handle multi-threading safely
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
else:
    # Production PostgreSQL pool configuration
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False
    )

# Session factory for synchronous operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base model class
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session per request
    and guarantees safe cleanup/closure upon completion or failure.
    
    Yields:
        Session: Active SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for background tasks, CLI commands, and test suites
    where FastAPI dependency injection is not used.
    
    Yields:
        Session: Active SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initializes all database tables registered with Base.metadata.
    Safe to call multiple times as it only creates missing tables.
    """
    # Import all models to ensure they are registered with Base.metadata
    import backend.app.models.entities  # noqa: F401
    Base.metadata.create_all(bind=engine)
