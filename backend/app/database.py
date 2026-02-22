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
        from .models.subscription import UserSubscription, SubscriptionPlan, SubscriptionHistory # Fix Mapper Error
        Base.metadata.create_all(bind=engine)
        
        # Auto-migrate: add new columns to existing tables
        _run_migrations()
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def _run_migrations():
    """
    Auto-migrate: compare SQLAlchemy model columns with actual DB columns
    and safely ADD any missing columns. This ensures updates NEVER require
    deleting the database, preserving admin credentials and user data.
    """
    from sqlalchemy import text, inspect as sa_inspect

    inspector = sa_inspect(engine)
    existing_tables = inspector.get_table_names()

    if not existing_tables:
        return  # Fresh database, create_all handled it

    # SQLAlchemy type -> SQLite type mapping
    type_map = {
        'INTEGER': 'INTEGER',
        'VARCHAR': 'VARCHAR(255)',
        'STRING': 'VARCHAR(255)',
        'TEXT': 'TEXT',
        'BOOLEAN': 'BOOLEAN',
        'FLOAT': 'FLOAT',
        'DATETIME': 'DATETIME',
        'JSON': 'JSON',
        'ENUM': 'VARCHAR(50)',
    }

    def get_sqlite_type(col):
        type_name = type(col.type).__name__.upper()
        if type_name in type_map:
            return type_map[type_name]
        if hasattr(col.type, 'length') and col.type.length:
            return f"VARCHAR({col.type.length})"
        return 'TEXT'

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                # New table — create_all should have handled it, but try anyway
                try:
                    table.create(bind=engine, checkfirst=True)
                    logger.info(f"✅ Migration: created table '{table.name}'")
                except Exception as e:
                    logger.warning(f"Migration skip table '{table.name}': {e}")
                continue

            # Compare columns
            existing_cols = {col['name'] for col in inspector.get_columns(table.name)}

            for col in table.columns:
                if col.name not in existing_cols:
                    col_type = get_sqlite_type(col)
                    default = ""
                    if col.default is not None:
                        try:
                            val = col.default.arg
                            if isinstance(val, bool):
                                default = f" DEFAULT {1 if val else 0}"
                            elif isinstance(val, (int, float)):
                                default = f" DEFAULT {val}"
                            elif isinstance(val, str):
                                default = f" DEFAULT '{val}'"
                        except Exception:
                            pass

                    try:
                        sql = f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}{default}"
                        conn.execute(text(sql))
                        logger.info(f"✅ Migration: added column '{col.name}' to '{table.name}'")
                    except Exception as e:
                        logger.warning(f"Migration skip {table.name}.{col.name}: {e}")


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
