"""
Activity Log API Endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from datetime import datetime
import json

from ..database import get_db
from ..models.user import User, ActivityLog
from ..utils.security import get_current_admin

router = APIRouter()


@router.get("/activity/recent")
async def get_recent_activity(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get recent activity logs"""
    activities = db.query(ActivityLog).order_by(
        desc(ActivityLog.created_at)
    ).limit(limit).all()
    
    return [
        {
            "id": a.id,
            "type": a.type,
            "description": a.description,
            "user": db.query(User).filter(User.id == a.user_id).first().username if a.user_id else "system",
            "timestamp": a.created_at.isoformat() if a.created_at else datetime.utcnow().isoformat(),
            "metadata": json.loads(a.metadata) if a.metadata else {}
        }
        for a in activities
    ]


@router.get("/activity/all")
async def get_all_activity(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all activity logs with pagination"""
    total = db.query(ActivityLog).count()
    activities = db.query(ActivityLog).order_by(
        desc(ActivityLog.created_at)
    ).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": [
            {
                "id": a.id,
                "type": a.type,
                "description": a.description,
                "user": db.query(User).filter(User.id == a.user_id).first().username if a.user_id else "system",
                "timestamp": a.created_at.isoformat() if a.created_at else datetime.utcnow().isoformat(),
                "ip_address": a.ip_address,
                "metadata": json.loads(a.metadata) if a.metadata else {}
            }
            for a in activities
        ]
    }


# Helper function to log activities
def log_activity(
    db: Session,
    type: str,
    description: str,
    user_id: int = None,
    ip_address: str = None,
    metadata: dict = None
):
    """Log an activity"""
    activity = ActivityLog(
        user_id=user_id,
        type=type,
        description=description,
        ip_address=ip_address,
        metadata=json.dumps(metadata) if metadata else None
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity
