"""
Activity Log API Endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from datetime import datetime

from ..database import get_db
from ..models.user import User
from ..utils.security import get_current_admin

router = APIRouter()


@router.get("/activity/recent")
async def get_recent_activity(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get recent activity logs"""
    # Mock data for now - implement database storage later
    return [
        {
            "id": 1,
            "type": "user_connected",
            "description": "User connected via OpenVPN",
            "user": "admin",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {"protocol": "OpenVPN", "ip": "192.168.1.100"}
        },
        {
            "id": 2,
            "type": "user_created",
            "description": "New user created",
            "user": "admin",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {"new_user": "test_user"}
        }
    ]


@router.get("/activity/all")
async def get_all_activity(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all activity logs with pagination"""
    return {
        "total": 0,
        "items": []
    }
