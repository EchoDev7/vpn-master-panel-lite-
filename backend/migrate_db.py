import logging
import sys
import os
from sqlalchemy import text, inspect

# Add backend directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_database():
    """
    Safely migrate the database by checking for missing columns and adding them.
    This replaces the fragile heredoc in update.sh.
    """
    logger.info("Starting database migration check...")
    
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        with engine.begin() as conn:
            # 1. Check traffic_logs table
            if 'traffic_logs' in existing_tables:
                columns = [col['name'] for col in inspector.get_columns('traffic_logs')]
                
                # Add traffic_type column
                if 'traffic_type' not in columns:
                    logger.info("Adding 'traffic_type' column to 'traffic_logs'...")
                    conn.execute(text("ALTER TABLE traffic_logs ADD COLUMN traffic_type VARCHAR(20) DEFAULT 'direct' NOT NULL"))
                
                # Add tunnel_id column
                if 'tunnel_id' not in columns:
                    logger.info("Adding 'tunnel_id' column to 'traffic_logs'...")
                    conn.execute(text("ALTER TABLE traffic_logs ADD COLUMN tunnel_id INTEGER"))
            
            # 2. Check users table
            if 'users' in existing_tables:
                columns = [col['name'] for col in inspector.get_columns('users')]
                
                # Add any missing user columns here if needed in future
                # Example:
                # if 'new_column' not in columns:
                #     conn.execute(text("ALTER TABLE users ADD COLUMN new_column ..."))
                pass

        logger.info("✅ Database migration completed successfully.")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_database()
