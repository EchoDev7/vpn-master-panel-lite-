"""
WebSocket Event Handlers
Handles different types of WebSocket events and messages
"""
from fastapi import WebSocket
from typing import Dict, Any
import logging
from datetime import datetime
from .manager import manager

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """Handles WebSocket events and messages"""
    
    @staticmethod
    async def handle_message(websocket: WebSocket, data: Dict[str, Any]):
        """Route incoming WebSocket messages to appropriate handlers"""
        message_type = data.get("type")
        
        if message_type == "pong":
            await WebSocketHandler.handle_pong(websocket, data)
        elif message_type == "subscribe":
            await WebSocketHandler.handle_subscribe(websocket, data)
        elif message_type == "unsubscribe":
            await WebSocketHandler.handle_unsubscribe(websocket, data)
        elif message_type == "notification_read":
            await WebSocketHandler.handle_notification_read(websocket, data)
        else:
            logger.warning(f"Unknown message type: {message_type}")
            
    @staticmethod
    async def handle_pong(websocket: WebSocket, data: Dict[str, Any]):
        """Handle pong response from client"""
        manager.update_last_ping(websocket)
        
    @staticmethod
    async def handle_subscribe(websocket: WebSocket, data: Dict[str, Any]):
        """Handle subscription to specific events"""
        # Future: implement event-specific subscriptions
        await manager.send_personal_message({
            "type": "subscribed",
            "events": data.get("events", []),
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
        
    @staticmethod
    async def handle_unsubscribe(websocket: WebSocket, data: Dict[str, Any]):
        """Handle unsubscription from specific events"""
        # Future: implement event-specific unsubscriptions
        await manager.send_personal_message({
            "type": "unsubscribed",
            "events": data.get("events", []),
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
        
    @staticmethod
    async def handle_notification_read(websocket: WebSocket, data: Dict[str, Any]):
        """Handle notification read event"""
        notification_id = data.get("notification_id")
        # This will be handled by the notification API
        logger.info(f"Notification {notification_id} marked as read via WebSocket")


# Event emitters for different types of events
class WebSocketEvents:
    """Helper class to emit WebSocket events"""
    
    @staticmethod
    async def emit_notification(user_id: int, notification: dict):
        """Emit a new notification to user"""
        message = {
            "type": "notification",
            "data": notification,
            "timestamp": datetime.utcnow().isoformat()
        }
        await manager.send_to_user(message, user_id)
        
    @staticmethod
    async def emit_user_created(user_data: dict):
        """Emit user created event to admins"""
        message = {
            "type": "user_created",
            "data": user_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await manager.broadcast_to_admins(message)
        
    @staticmethod
    async def emit_user_updated(user_data: dict):
        """Emit user updated event to admins"""
        message = {
            "type": "user_updated",
            "data": user_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await manager.broadcast_to_admins(message)
        
    @staticmethod
    async def emit_user_deleted(user_id: int):
        """Emit user deleted event to admins"""
        message = {
            "type": "user_deleted",
            "data": {"user_id": user_id},
            "timestamp": datetime.utcnow().isoformat()
        }
        await manager.broadcast_to_admins(message)
        
    @staticmethod
    async def emit_connection_status(connection_data: dict):
        """Emit connection status update to admins"""
        message = {
            "type": "connection_status",
            "data": connection_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await manager.broadcast_to_admins(message)
        
    @staticmethod
    async def emit_traffic_update(traffic_data: dict):
        """Emit traffic update to admins"""
        message = {
            "type": "traffic_update",
            "data": traffic_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await manager.broadcast_to_admins(message)
        
    @staticmethod
    async def emit_system_alert(alert_data: dict):
        """Emit system alert to all admins"""
        message = {
            "type": "system_alert",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await manager.broadcast_to_admins(message)
        
    @staticmethod
    async def emit_activity(activity_data: dict):
        """Emit activity log to admins"""
        message = {
            "type": "activity",
            "data": activity_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await manager.broadcast_to_admins(message)
