"""
WebSocket Connection Manager
Handles WebSocket connections, broadcasting, and connection lifecycle
"""
from typing import Dict, Set, Optional
from fastapi import WebSocket
import json
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Store admin connections separately
        self.admin_connections: Set[WebSocket] = set()
        # Connection metadata
        self.connection_metadata: Dict[WebSocket, dict] = {}
        
    async def connect(self, websocket: WebSocket, user_id: int, is_admin: bool = False):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        # Add to user connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        
        # Add to admin connections if admin
        if is_admin:
            self.admin_connections.add(websocket)
        
        # Store metadata
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "is_admin": is_admin,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        
        logger.info(f"WebSocket connected: user_id={user_id}, is_admin={is_admin}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
        
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        metadata = self.connection_metadata.get(websocket)
        if not metadata:
            return
            
        user_id = metadata["user_id"]
        is_admin = metadata["is_admin"]
        
        # Remove from user connections
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove from admin connections
        if is_admin:
            self.admin_connections.discard(websocket)
        
        # Remove metadata
        del self.connection_metadata[websocket]
        
        logger.info(f"WebSocket disconnected: user_id={user_id}")
        
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
            
    async def send_to_user(self, message: dict, user_id: int):
        """Send a message to all connections of a specific user"""
        if user_id not in self.active_connections:
            return
            
        disconnected = set()
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)
            
    async def broadcast_to_admins(self, message: dict):
        """Broadcast a message to all admin connections"""
        disconnected = set()
        for websocket in self.admin_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to admin: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)
            
    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all connected clients"""
        disconnected = set()
        for websocket in self.connection_metadata.keys():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to all: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)
            
    def get_active_users(self) -> int:
        """Get count of users with active connections"""
        return len(self.active_connections)
        
    def get_active_connections(self) -> int:
        """Get total count of active WebSocket connections"""
        return len(self.connection_metadata)
        
    def get_admin_connections(self) -> int:
        """Get count of active admin connections"""
        return len(self.admin_connections)
        
    async def ping_all(self):
        """Send ping to all connections to keep them alive"""
        message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_all(message)
        
    def update_last_ping(self, websocket: WebSocket):
        """Update last ping time for a connection"""
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["last_ping"] = datetime.utcnow()


# Global connection manager instance
manager = ConnectionManager()


async def start_heartbeat():
    """Background task to send periodic pings"""
    while True:
        await asyncio.sleep(30)  # Ping every 30 seconds
        await manager.ping_all()
