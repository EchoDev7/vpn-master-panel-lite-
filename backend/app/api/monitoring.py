"""
Monitoring API Endpoints - Real-time system and VPN monitoring
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any
from datetime import datetime, timedelta

from ..database import get_db
from ..models.user import User, ConnectionLog, TrafficLog
from ..utils.security import get_current_admin

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get dashboard statistics"""
    # Total users
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.status == "active").count()
    
    # Active connections
    active_connections = db.query(ConnectionLog).filter(
        ConnectionLog.is_active == True
    ).count()
    
    # Total traffic (last 24h)
    day_ago = datetime.utcnow() - timedelta(days=1)
    traffic_24h = db.query(
        func.sum(TrafficLog.upload_bytes + TrafficLog.download_bytes)
    ).filter(
        TrafficLog.recorded_at >= day_ago
    ).scalar() or 0
    
    # System stats
    import psutil
    
    return {
        "users": {
            "total": total_users,
            "active": active_users
        },
        "connections": {
            "active": active_connections
        },
        "traffic": {
            "bytes_24h": traffic_24h,
            "gb_24h": round(traffic_24h / (1024**3), 2)
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/active-connections")
async def get_active_connections(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get list of active connections"""
    connections = db.query(ConnectionLog).filter(
        ConnectionLog.is_active == True
    ).all()
    
    result = []
    for conn in connections:
        result.append({
            "user_id": conn.user_id,
            "username": conn.user.username if conn.user else None,
            "protocol": conn.protocol,
            "client_ip": conn.client_ip,
            "virtual_ip": conn.virtual_ip,
            "connected_at": conn.connected_at.isoformat() if conn.connected_at else None
        })
    
    return result


@router.get("/traffic-stats")
async def get_traffic_stats(
    days: int = 7,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get traffic statistics for the last N days"""
    from sqlalchemy import func, cast, Date
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Group by date
    daily_traffic = db.query(
        cast(TrafficLog.recorded_at, Date).label('date'),
        func.sum(TrafficLog.upload_bytes).label('upload'),
        func.sum(TrafficLog.download_bytes).label('download')
    ).filter(
        TrafficLog.recorded_at >= start_date
    ).group_by(
        cast(TrafficLog.recorded_at, Date)
    ).all()
    
    result = []
    for day in daily_traffic:
        result.append({
            "date": day.date.isoformat(),
            "upload_gb": round((day.upload or 0) / (1024**3), 2),
            "download_gb": round((day.download or 0) / (1024**3), 2),
            "total_gb": round(((day.upload or 0) + (day.download or 0)) / (1024**3), 2)
        })
    
    return result
