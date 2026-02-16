"""
Email Service
SMTP email sending with templates
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader, select_autoescape
import logging
from pathlib import Path
from typing import List, Optional
import os

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending notifications"""
    
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('SMTP_FROM', self.smtp_user)
        self.from_name = os.getenv('SMTP_FROM_NAME', 'VPN Master Panel')
        
        # Setup Jinja2 for templates
        template_dir = Path(__file__).parent.parent / 'templates' / 'emails'
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """Send an email"""
        try:
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f'{self.from_name} <{self.from_email}>'
            message['To'] = to_email
            
            # Add text version
            if text_body:
                part1 = MIMEText(text_body, 'plain')
                message.attach(part1)
            
            # Add HTML version
            part2 = MIMEText(html_body, 'html')
            message.attach(part2)
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=True
            )
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def send_template_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: dict
    ) -> bool:
        """Send email using template"""
        try:
            template = self.jinja_env.get_template(f'{template_name}.html')
            html_body = template.render(**context)
            
            return await self.send_email(to_email, subject, html_body)
            
        except Exception as e:
            logger.error(f"Failed to send template email: {e}")
            return False
    
    async def send_user_created_email(self, user_email: str, username: str, password: str):
        """Send welcome email to new user"""
        return await self.send_template_email(
            to_email=user_email,
            subject='Welcome to VPN Master Panel',
            template_name='user_created',
            context={
                'username': username,
                'password': password,
                'panel_url': os.getenv('PANEL_URL', 'http://localhost:3000')
            }
        )
    
    async def send_expiry_warning_email(self, user_email: str, username: str, days_left: int):
        """Send expiry warning email"""
        return await self.send_template_email(
            to_email=user_email,
            subject=f'Your VPN account expires in {days_left} days',
            template_name='user_expiring',
            context={
                'username': username,
                'days_left': days_left
            }
        )
    
    async def send_traffic_limit_email(self, user_email: str, username: str, usage_percent: int):
        """Send traffic limit warning email"""
        return await self.send_template_email(
            to_email=user_email,
            subject='VPN Traffic Limit Warning',
            template_name='traffic_limit',
            context={
                'username': username,
                'usage_percent': usage_percent
            }
        )


# Global email service instance
email_service = EmailService()
