"""
Users API Endpoints - CRUD operations for VPN users
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime, timedelta
from typing import List, Optional

from ..database import get_db
from ..models.user import User, UserRole, UserStatus
from ..utils.security import (
    get_current_admin,
    get_current_user,
    get_password_hash
)
from .activity import log_activity
from .notifications import create_notification

router = APIRouter()


# Request/Response Models
class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    
    # Limits
    data_limit_gb: float = 0  # 0 = unlimited
    connection_limit: int = 1
    speed_limit_mbps: int = 0 # 0 = unlimited
    expiry_days: Optional[int] = 30
    
    # Protocol settings (OpenVPN only)
    openvpn_enabled: bool = True
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if not v.isalnum() and '_' not in v:
            raise ValueError('Username must be alphanumeric')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    
    # Limits
    data_limit_gb: Optional[float] = None
    connection_limit: Optional[int] = None
    speed_limit_mbps: Optional[int] = None
    expiry_date: Optional[datetime] = None
    expiry_days: Optional[int] = None
    
    # Status
    status: Optional[UserStatus] = None
    
    # Protocol settings (OpenVPN only)
    openvpn_enabled: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: UserRole
    status: UserStatus
    
    data_limit_gb: Optional[float] = 0
    connection_limit: Optional[int] = 1
    expiry_date: Optional[datetime] = None
    
    total_upload_bytes: Optional[int] = 0
    total_download_bytes: Optional[int] = 0
    data_usage_gb: Optional[float] = 0
    
    openvpn_enabled: Optional[bool] = False
    
    created_at: datetime
    last_connection: Optional[datetime] = None
    is_online: Optional[bool] = False
    subscription_token: Optional[str] = None
    
    class Config:
        from_attributes = True
        
    @field_validator('data_limit_gb', 'total_upload_bytes', 'total_download_bytes', 'data_usage_gb', mode='before')
    def set_default_zero(cls, v):
        return v or 0
        
    @field_validator('connection_limit', mode='before')
    def set_default_one(cls, v):
        return v or 1
        
    @field_validator('openvpn_enabled', mode='before')
    def set_default_false(cls, v):
        if v is None:
            return False
        return v


class UserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    users: List[UserResponse]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Create new VPN user (Admin only)
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email already exists
    if user_data.email:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
    
    # Calculate expiry date
    expiry_date = None
    if user_data.expiry_days and user_data.expiry_days > 0:
        expiry_date = datetime.utcnow() + timedelta(days=user_data.expiry_days)
    
    # Create user
    new_user = User(
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        data_limit_gb=user_data.data_limit_gb,
        connection_limit=user_data.connection_limit,
        expiry_date=expiry_date,
        openvpn_enabled=user_data.openvpn_enabled,
        created_by=current_admin.id
    )

    # Generate subscription token
    import secrets
    new_user.subscription_token = secrets.token_urlsafe(32)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Auto-Provisioning Pipeline (F5 - User Requested)
    try:
        import asyncio
        from ..services.users import _provision_new_user
        asyncio.create_task(_provision_new_user(new_user.id))
    except Exception as e:
        # Don't fail the request if async task logic has issues (e.g. event loop)
        pass

    return new_user




@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    List all users with pagination and filters (Admin only)
    """
    query = db.query(User)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
        )
    
    if role:
        query = query.filter(User.role == role)
    
    if status:
        query = query.filter(User.status == status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    users = query.offset(offset).limit(page_size).all()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "users": users
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Get user by ID (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Update user (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    
    # Hash password if provided
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
    # Handle expiry_days
    if "expiry_days" in update_data:
        days = update_data.pop("expiry_days")
        if days is not None and days > 0:
            update_data["expiry_date"] = datetime.utcnow() + timedelta(days=days)
        elif days == 0:
            update_data["expiry_date"] = None # Unlimited
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    # Log activity
    log_activity(
        db=db,
        type="user_updated",
        description=f"User '{user.username}' was updated",
        user_id=current_admin.id,
        ip_address=request.client.host if request.client else None,
        metadata={"updated_user_id": user.id, "username": user.username}
    )
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Delete user (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting super admin
    if user.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete super admin"
        )
    
    username = user.username  # Store before deletion
    
    db.delete(user)
    db.commit()
    
    # Log activity
    log_activity(
        db=db,
        type="user_deleted",
        description=f"User '{username}' was deleted",
        user_id=current_admin.id,
        ip_address=request.client.host if request.client else None,
        metadata={"deleted_user_id": user_id, "username": username}
    )
    
    # Create notification
    create_notification(
        db=db,
        type="warning",
        title="User Deleted",
        message=f"User '{username}' has been removed from the system",
        user_id=None
    )
    
    return None


@router.post("/{user_id}/reset-traffic", response_model=UserResponse)
async def reset_user_traffic(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Reset user traffic usage (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.total_upload_bytes = 0
    user.total_download_bytes = 0
    
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/{user_id}/regenerate-token", response_model=UserResponse)
async def regenerate_token(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Regenerate subscription token for user (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    import secrets
    user.subscription_token = secrets.token_urlsafe(16)
    db.commit()
    db.refresh(user)
    
    return user


# --- Config Download Endpoints ---

@router.get("/{user_id}/config/openvpn", response_model=dict)
async def get_openvpn_config(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get OpenVPN configuration for user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.openvpn_enabled:
        raise HTTPException(status_code=400, detail="OpenVPN is not enabled for this user")
        
    from ..services.openvpn import openvpn_service
    config_content = openvpn_service.generate_client_config(
        username=user.username
    )
    
    return {
        "filename": f"{user.username}.ovpn",
        "content": config_content
    }


# --- Ultimate User Management (Phase 3) ---

class BulkActionRequest(BaseModel):
    user_ids: List[int]
    action: str  # 'delete', 'enable', 'disable', 'reset_traffic'

@router.post("/bulk-action", status_code=status.HTTP_200_OK)
async def bulk_action(
    request: BulkActionRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Perform bulk actions on users (Admin only)
    """
    users = db.query(User).filter(User.id.in_(request.user_ids)).all()
    count = 0
    
    for user in users:
        # Skip super admin for destructive actions
        if user.role == UserRole.SUPER_ADMIN and request.action in ['delete', 'disable']:
            continue
            
        if request.action == 'delete':
            db.delete(user)
        elif request.action == 'enable':
            user.status = UserStatus.ACTIVE
        elif request.action == 'disable':
            user.status = UserStatus.DISABLED
        elif request.action == 'reset_traffic':
            user.total_upload_bytes = 0
            user.total_download_bytes = 0
        
        count += 1
    
    db.commit()
    
    return {"message": f"Action '{request.action}' performed on {count} users"}


@router.get("/{user_id}/details")
async def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Get detailed user profile including stats history (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    from ..models.user import ConnectionLog
    
    # Get last 5 connections
    recent_connections = db.query(ConnectionLog).filter(
        ConnectionLog.user_id == user_id
    ).order_by(ConnectionLog.connected_at.desc()).limit(5).all()
    
    return {
        "user": UserResponse.model_validate(user),
        "recent_connections": recent_connections,
        "stats": {
            "total_traffic_gb": user.total_traffic_gb,
            "avg_daily_usage_gb": 0, # Placeholder for now
            "days_until_expiry": (user.expiry_date - datetime.utcnow()).days if user.expiry_date else None
        }
    }


@router.get("/{user_id}/connections")
async def get_user_connections(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Get paginated connection logs for a user (Admin only)
    """
    from ..models.user import ConnectionLog
    
    query = db.query(ConnectionLog).filter(ConnectionLog.user_id == user_id).order_by(ConnectionLog.connected_at.desc())
    
    total = query.count()
    offset = (page - 1) * page_size
    logs = query.offset(offset).limit(page_size).all()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "logs": logs
    }


# --- Phase 4: Diagnostics & Control ---

@router.get("/{user_id}/logs")
async def get_user_logs(
    user_id: int,
    lines: int = 100,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Get raw connection logs filtered for this user (Admin only).
    Scans auth.log first (for auth attempts), then openvpn.log (for session details).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    logs = []
    
    # helper to run grep
    def grep_file(filepath, pattern, n_lines):
        if not os.path.exists(filepath):
            return []
        try:
            # We use a shell pipeline: grep "pattern" file | tail -n lines
            # Use specific list arguments for security where possible, but pipeline needs checks
            # Simplest: use grep's own max count? No, we want latest.
            import subprocess
            
            # 1. Grep all matches
            cmd_grep = ["grep", pattern, filepath]
            p1 = subprocess.Popen(cmd_grep, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # 2. Tail the last N
            cmd_tail = ["tail", "-n", str(n_lines)]
            p2 = subprocess.Popen(cmd_tail, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            p1.stdout.close() # Allow p1 to receive SIGPIPE if p2 exits.
            output, _ = p2.communicate()
            
            return output.splitlines()
        except Exception as e:
            return [f"Error reading {os.path.basename(filepath)}: {str(e)}"]

    import os
    
    # 1. Check Auth Log (High value)
    auth_logs = grep_file("/var/log/openvpn/auth.log", user.username, lines)
    if auth_logs:
        logs.extend([f"--- Auth Logs for {user.username} ---"] + auth_logs)
        
    # 2. Check System Log (Context)
    # This is noisier, maybe only if auth logs are empty or requested?
    # Let's include it but limit it.
    sys_logs = grep_file("/var/log/openvpn/openvpn.log", user.username, 20)
    if sys_logs:
         logs.extend([f"\n--- System Logs for {user.username} ---"] + sys_logs)
         
    if not logs:
        logs = ["No recent connection attempts found in logs."]
        
    return {"logs": logs}


@router.post("/{user_id}/kill")
async def kill_user_session(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Kill active OpenVPN session for user (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    results = []
    
    # OpenVPN Kill via Management Interface
    if user.openvpn_enabled:
        try:
            import socket
            # Connect to OpenVPN Management Interface
            # Default: localhost 7505
            mgmt_host = "127.0.0.1"
            mgmt_port = 7505
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                result = s.connect_ex((mgmt_host, mgmt_port))
                if result == 0:
                    # connection successful
                    # Read banner
                    s.recv(1024)
                    
                    # specific command to kill by common name
                    # "kill <common_name>"
                    cmd = f"kill {user.username}\n".encode()
                    s.sendall(cmd)
                    
                    response = s.recv(1024).decode()
                    if "SUCCESS" in response:
                        results.append("OpenVPN: Session Killed")
                    else:
                        results.append(f"OpenVPN: {response.strip()}")
                        
                    s.sendall(b"quit\n")
                else:
                    results.append("OpenVPN: Management Interface Unreachable")
        except Exception as e:
            results.append(f"OpenVPN Error: {str(e)}")
        
    return {"status": "completed", "results": results}

