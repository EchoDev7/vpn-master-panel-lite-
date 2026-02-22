import asyncio
import logging
from typing import Optional

from ..database import get_db_context
from ..models.user import User
from ..services.openvpn import openvpn_service
from ..services.email import email_service
from ..services.telegram import telegram_service

logger = logging.getLogger(__name__)

async def _provision_new_user(user_id: int):
    """
    Auto-provision a newly created user (F5):
    1. Send Welcome Email (optional)
    2. Notify Admin via Telegram
    """
    logger.info(f"Starting provisioning for user_id={user_id}")
    
    # We use a new DB session since this runs in background
    with get_db_context() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"Provisioning failed: User {user_id} not found")
            return

        # 1. Send Welcome Email
        if user.email:
            try:
                # Generate OpenVPN config content to attach/include
                ovpn_config = ""
                if user.openvpn_enabled:
                    ovpn_config = openvpn_service.generate_client_config(user.username)
                
                # Check if email service is configured
                if email_service.smtp_server:
                     await email_service.send_welcome_email(
                        to=user.email,
                        username=user.username,
                        ovpn_config=ovpn_config,
                        subscription_url=f"/sub/{user.subscription_token}" if user.subscription_token else "#"
                    )
                     logger.info(f"Welcome email sent to {user.email}")
            except Exception as e:
                logger.error(f"Welcome email failed for {user.username}: {e}")

        # 2. Notify Admin via Telegram
        try:
            expiry_str = user.expiry_date.strftime("%Y-%m-%d") if user.expiry_date else "Unlimited/Never"
            limit_str = f"{user.data_limit_gb} GB" if user.data_limit_gb > 0 else "Unlimited"
            
            msg = (
                f"✅ <b>New User Created</b>\n"
                f"👤 <b>Username:</b> {user.username}\n"
                f"📊 <b>Data:</b> {limit_str}\n"
                f"📅 <b>Expiry:</b> {expiry_str}\n"
                f"🔗 <b>Sub Link:</b> /sub/{user.subscription_token}"
            )
            # Assuming telegram_service has a method to notify admins
            # If not, we might need to add it or use `send_message` to a configured admin ID
            await telegram_service.send_admin_alert(msg)
            logger.info("Telegram notification sent")
            
        except Exception as e:
            # It's possible send_admin_alert doesn't exist or failed
            logger.error(f"Telegram notify failed: {e}")

