"""
Database setup with SQLAlchemy ORM
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator
import logging

from .config import settings

logger = logging.getLogger(__name__)

# Choose database based on settings
if settings.USE_SQLITE:
    DATABASE_URL = settings.SQLITE_URL
    engine_kwargs = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
else:
    DATABASE_URL = settings.DATABASE_URL
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    }

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    **engine_kwargs
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# Dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    Dependency function that yields database sessions.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    Usage: with get_db_context() as db: ...
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


def init_db():
    """Initialize database - create all tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def drop_db():
    """Drop all tables - USE WITH CAUTION!"""
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")


# Enable foreign keys for SQLite
if settings.USE_SQLITE:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
