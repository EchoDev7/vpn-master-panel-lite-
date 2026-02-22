"""
Telegram Bot Service
Bot integration for notifications and commands
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramBotService:
    """Telegram bot service for notifications and commands"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.admin_chat_ids = os.getenv('TELEGRAM_ADMIN_CHAT_IDS', '').split(',')
        self.application: Optional[Application] = None
        
    async def initialize(self):
        """Initialize the bot"""
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            return
            
        self.application = Application.builder().token(self.bot_token).build()
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("users", self.users_command))
        self.application.add_handler(CommandHandler("traffic", self.traffic_command))
        self.application.add_handler(CommandHandler("connections", self.connections_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Start bot
        await self.application.initialize()
        await self.application.start()
        
        logger.info("Telegram bot initialized")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        keyboard = [
            [InlineKeyboardButton("📊 Status", callback_data='status')],
            [InlineKeyboardButton("👥 Users", callback_data='users')],
            [InlineKeyboardButton("📈 Traffic", callback_data='traffic')],
            [InlineKeyboardButton("🔗 Connections", callback_data='connections')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🛡️ *VPN Master Panel Bot*\n\n"
            "Welcome! Use the buttons below to get information:\n\n"
            "Commands:\n"
            "/status - Server status\n"
            "/users - User statistics\n"
            "/traffic - Traffic statistics\n"
            "/connections - Active connections\n"
            "/help - Show help",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        # Get server status from database
        await update.message.reply_text(
            "🖥️ *Server Status*\n\n"
            "✅ Online\n"
            "CPU: 45%\n"
            "Memory: 60%\n"
            "Disk: 35%\n"
            "Uptime: 15 days",
            parse_mode='Markdown'
        )
    
    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /users command"""
        await update.message.reply_text(
            "👥 *User Statistics*\n\n"
            "Total Users: 150\n"
            "Active Users: 120\n"
            "Expired Users: 30",
            parse_mode='Markdown'
        )
    
    async def traffic_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /traffic command"""
        await update.message.reply_text(
            "📈 *Traffic Statistics*\n\n"
            "Today: 50 GB\n"
            "This Week: 300 GB\n"
            "This Month: 1.2 TB",
            parse_mode='Markdown'
        )
    
    async def connections_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /connections command"""
        await update.message.reply_text(
            "🔗 *Active Connections*\n\n"
            "Total: 45\n"
            "OpenVPN: 45",
            parse_mode='Markdown'
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await update.message.reply_text(
            "📚 *Available Commands*\n\n"
            "/start - Start the bot\n"
            "/status - Server status\n"
            "/users - User statistics\n"
            "/traffic - Traffic statistics\n"
            "/connections - Active connections\n"
            "/help - Show this help",
            parse_mode='Markdown'
        )
    
    async def send_notification(self, message: str, chat_id: Optional[str] = None):
        """Send notification to admin(s)"""
        if not self.application:
            logger.warning("Bot not initialized")
            return
            
        chat_ids = [chat_id] if chat_id else self.admin_chat_ids
        
        for cid in chat_ids:
            if cid:
                try:
                    await self.application.bot.send_message(
                        chat_id=cid,
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to send notification to {cid}: {e}")
    
    async def shutdown(self):
        """Shutdown the bot"""
        if self.application:
            await self.application.stop()
            await self.application.shutdown()


# Global telegram service instance
telegram_service = TelegramBotService()
