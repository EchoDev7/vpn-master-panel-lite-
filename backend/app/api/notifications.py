"""
Notifications API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from datetime import datetime

from ..database import get_db
from ..models.user import User
from ..utils.security import get_current_admin

router = APIRouter()


# Notification model (add to models/user.py later)
class Notification:
    """Mock notification for now - will be added to database"""
    pass


@router.get("/notifications")
async def get_notifications(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all notifications for current user"""
    # Mock data for now - implement database storage later
    return [
        {
            "id": 1,
            "type": "success",
            "title": "New User Connected",
            "message": "User connected successfully via OpenVPN",
            "timestamp": datetime.utcnow().isoformat(),
            "read": False
        }
    ]


@router.get("/notifications/unread-count")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get count of unread notifications"""
    # Mock data
    return {"count": 2}


@router.post("/notifications/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Mark notification as read"""
    return {"success": True}


@router.post("/notifications/read-all")
async def mark_all_as_read(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Mark all notifications as read"""
    return {"success": True}


@router.delete("/notifications")
async def clear_all_notifications(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Clear all notifications"""
    return {"success": True}
