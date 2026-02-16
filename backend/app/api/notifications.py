"""
Notifications API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from datetime import datetime

from ..database import get_db
from ..models.user import User, Notification
from ..utils.security import get_current_admin

router = APIRouter()


@router.get("/notifications")
async def get_notifications(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all notifications for current user"""
    # Get notifications for this user or system-wide notifications
    notifications = db.query(Notification).filter(
        (Notification.user_id == current_admin.id) | (Notification.user_id == None)
    ).order_by(desc(Notification.created_at)).limit(limit).all()
    
    return [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "timestamp": n.created_at.isoformat() if n.created_at else datetime.utcnow().isoformat(),
            "read": n.read
        }
        for n in notifications
    ]


@router.get("/notifications/unread-count")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get count of unread notifications"""
    count = db.query(Notification).filter(
        ((Notification.user_id == current_admin.id) | (Notification.user_id == None)),
        Notification.read == False
    ).count()
    
    return {"count": count}


@router.post("/notifications/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Mark notification as read"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        ((Notification.user_id == current_admin.id) | (Notification.user_id == None))
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    
    return {"success": True}


@router.post("/notifications/read-all")
async def mark_all_as_read(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Mark all notifications as read"""
    db.query(Notification).filter(
        ((Notification.user_id == current_admin.id) | (Notification.user_id == None)),
        Notification.read == False
    ).update({"read": True, "read_at": datetime.utcnow()})
    db.commit()
    
    return {"success": True}


@router.delete("/notifications")
async def clear_all_notifications(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Clear all notifications for current user"""
    db.query(Notification).filter(
        Notification.user_id == current_admin.id
    ).delete()
    db.commit()
    
    return {"success": True}


# Helper function to create notifications
def create_notification(
    db: Session,
    type: str,
    title: str,
    message: str,
    user_id: int = None
):
    """Create a new notification"""
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
