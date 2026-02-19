import asyncio
import logging
from datetime import datetime, timezone
from ..database import get_db_context
from ..models.user import User, UserStatus

logger = logging.getLogger(__name__)

class LightweightScheduler:
    """
    A simple in-memory scheduler for periodic tasks.
    Replaces Celery Beat for the Lite edition.
    """

    def __init__(self):
        self._check_interval = 60  # seconds
        self._is_running = False

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

    async def check_expired_users(self):
        """
        Check for users whose expiry date has passed and suspend them.

        Uses get_db_context() to guarantee the session is always closed.
        Collects user info before closing the DB context, then calls
        traffic_monitor to terminate live sessions OUTSIDE the DB context
        (avoids subprocess/socket calls holding the DB connection open).
        """
        users_to_terminate = []

        try:
            now_utc = datetime.now(timezone.utc)

            with get_db_context() as db:
                # SQLAlchemy stores expiry_date as timezone-aware (UTC).
                # We query against the raw column using _sa_instance_state-safe
                # column reference (not the Python @property).
                active_users = db.query(User).filter(
                    User.status == UserStatus.ACTIVE,
                    User.expiry_date.isnot(None),
                ).all()

                expired = []
                for user in active_users:
                    expiry = user.expiry_date
                    if expiry is None:
                        continue
                    # Normalize: if DB returned naive datetime, treat as UTC
                    if expiry.tzinfo is None:
                        expiry = expiry.replace(tzinfo=timezone.utc)
                    if now_utc > expiry:
                        expired.append(user)

                if expired:
                    logger.info(f"Scheduler: found {len(expired)} expired user(s).")
                    for user in expired:
                        user.status = UserStatus.EXPIRED
                        logger.info(f"User {user.username} expired. Disabling access.")
                        users_to_terminate.append({
                            "username": user.username,
                            "openvpn_enabled": user.openvpn_enabled,
                            "wireguard_enabled": user.wireguard_enabled,
                            "wireguard_public_key": user.wireguard_public_key,
                        })
                    # Commit status change before terminating sessions
                    db.commit()

        except Exception as e:
            logger.error(f"Error checking expired users: {e}")

        # Terminate live sessions OUTSIDE the DB context (no deadlock risk).
        if users_to_terminate:
            try:
                from .monitoring import traffic_monitor
                for user_info in users_to_terminate:
                    traffic_monitor._terminate_user_sessions_by_info(user_info)
            except Exception as e:
                logger.error(f"Error terminating sessions for expired users: {e}")


scheduler = LightweightScheduler()
