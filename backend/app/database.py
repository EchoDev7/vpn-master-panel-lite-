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
        from .models.user import User
        from .models.vpn_server import VPNServer, Tunnel
        Base.metadata.create_all(bind=engine)
        
        # Auto-migrate: add new columns to existing tables
        _run_migrations()
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def _run_migrations():
    """Add new columns to existing tables (safe to run multiple times)"""
    from sqlalchemy import text, inspect
    
    inspector = inspect(engine)
    
    # Check if 'users' table exists
    if 'users' not in inspector.get_table_names():
        return
    
    existing_columns = [col['name'] for col in inspector.get_columns('users')]
    
    migrations = [
        ("wireguard_preshared_key", "VARCHAR(255)"),
    ]
    
    with engine.begin() as conn:
        for col_name, col_type in migrations:
            if col_name not in existing_columns:
                try:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                    logger.info(f"✅ Migration: added column '{col_name}' to users table")
                except Exception as e:
                    logger.warning(f"Migration skip: {col_name} — {e}")


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
