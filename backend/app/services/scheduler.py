import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.user import User, UserStatus
from ..services.monitoring import MonitoringService

logger = logging.getLogger(__name__)

class LightweightScheduler:
    """
    A simple in-memory scheduler for periodic tasks.
    Replaces Celery Beat for the Lite edition.
    """
    
    def __init__(self):
        self._check_interval = 60  # seconds
        self._is_running = False
        self._monitoring_service = MonitoringService()

    async def start(self):
        """Start the scheduler loop"""
        if self._is_running:
            return
            
        self._is_running = True
        logger.info("✅ Lightweight Scheduler started")
        
        while self._is_running:
            try:
                await self.run_tasks()
            except Exception as e:
                logger.error(f"❌ Scheduler error: {e}")
            
            await asyncio.sleep(self._check_interval)

    async def stop(self):
        """Stop the scheduler loop"""
        self._is_running = False
        logger.info("🛑 Lightweight Scheduler stopped")

    async def run_tasks(self):
        """Execute periodic tasks sequentially"""
        # 1. Check expired users
        await self.check_expired_users()
        
        # 2. Monitor traffic (optional/simplified)
        # await self._monitoring_service.update_stats() 

    async def check_expired_users(self):
        """Check for users whose expiry date has passed"""
        db = SessionLocal()
        try:
            current_time = datetime.utcnow()
            expired_users = db.query(User).filter(
                User.status == UserStatus.ACTIVE,
                User.expiry_date != None,
                User.expiry_date < current_time
            ).all()

            if expired_users:
                logger.info(f"Checking expiry: Found {len(expired_users)} expired users.")
                for user in expired_users:
                    user.status = UserStatus.EXPIRED
                    logger.info(f"User {user.username} expired. Disabling access.")
                    # TODO: Call protocol specific disable logic here (e.g. revoke VPN access)
                
                db.commit()
                
        except Exception as e:
            logger.error(f"Error checking expired users: {e}")
        finally:
            db.close()

scheduler = LightweightScheduler()
