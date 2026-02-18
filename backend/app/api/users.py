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
    expiry_days: Optional[int] = 30
    
    # Protocol settings
    openvpn_enabled: bool = True
    wireguard_enabled: bool = True
    l2tp_enabled: bool = False
    cisco_enabled: bool = False
    
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
    expiry_date: Optional[datetime] = None
    expiry_days: Optional[int] = None
    
    # Status
    status: Optional[UserStatus] = None
    
    # Protocol settings
    openvpn_enabled: Optional[bool] = None
    wireguard_enabled: Optional[bool] = None
    l2tp_enabled: Optional[bool] = None
    cisco_enabled: Optional[bool] = None


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
    wireguard_enabled: Optional[bool] = False
    l2tp_enabled: Optional[bool] = False
    cisco_enabled: Optional[bool] = False
    
    created_at: datetime
    last_connection: Optional[datetime] = None
    is_online: Optional[bool] = False
    
    class Config:
        from_attributes = True
        
    @field_validator('data_limit_gb', 'total_upload_bytes', 'total_download_bytes', 'data_usage_gb', mode='before')
    def set_default_zero(cls, v):
        return v or 0
        
    @field_validator('connection_limit', mode='before')
    def set_default_one(cls, v):
        return v or 1
        
    @field_validator('openvpn_enabled', 'wireguard_enabled', 'l2tp_enabled', 'cisco_enabled', mode='before')
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
        wireguard_enabled=user_data.wireguard_enabled,
        l2tp_enabled=user_data.l2tp_enabled,
        cisco_enabled=user_data.cisco_enabled,
        created_by=current_admin.id
    )
    
    # Generate WireGuard keys if enabled
    if user_data.wireguard_enabled:
        try:
            from ..services.wireguard import generate_wireguard_keys
            keys = generate_wireguard_keys()
            new_user.wireguard_private_key = keys['private_key']
            new_user.wireguard_public_key = keys['public_key']
            new_user.wireguard_ip = keys['ip']
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to generate WireGuard keys: {e}. Disabling WireGuard for this user.")
            new_user.wireguard_enabled = False
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Log activity
    log_activity(
        db=db,
        type="user_created",
        description=f"User {new_user.username} created by {current_admin.username}",
        user_id=current_admin.id,
        ip_address=request.client.host if request.client else None,
        metadata={"new_user_id": new_user.id}
    )
    
    # Send email notification (async, non-blocking)
    if new_user.email:
        try:
            from ..services.email import email_service
            import asyncio
            asyncio.create_task(
                email_service.send_user_created_email(
                    user_email=new_user.email,
                    username=new_user.username,
                    password=user_data.password  # Send original password
                )
            )
        except Exception as e:
            logger.warning(f"Failed to send welcome email: {e}")
    
    # Send WebSocket notification to admins
    try:
        from ..websocket.handlers import WebSocketEvents
        import asyncio
        asyncio.create_task(
            WebSocketEvents.emit_user_created({
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "role": new_user.role.value
            })
        )
    except Exception as e:
        logger.warning(f"Failed to send WebSocket notification: {e}")
    
    # Create notification
    create_notification(
        db=db,
        type="success",
        title="New User Created",
        message=f"User '{new_user.username}' was successfully created",
        user_id=None  # System-wide notification
    )
    
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


@router.get("/{user_id}/config/wireguard", response_model=dict)
async def get_wireguard_config(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get WireGuard configuration for user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Auto-enable WireGuard for the user if not enabled
    if not user.wireguard_enabled:
        user.wireguard_enabled = True
        db.commit()
        db.refresh(user)

    from ..services.wireguard import wireguard_service

    # Auto-generate keys if missing
    if not user.wireguard_private_key:
        try:
            keys = wireguard_service.generate_keypair()
            user.wireguard_private_key = keys['private_key']
            user.wireguard_public_key = keys['public_key']

            # Allocate IP
            try:
                user.wireguard_ip = wireguard_service.allocate_ip()
            except Exception:
                # Fallback: simple IP allocation based on user ID
                user.wireguard_ip = f"10.66.66.{(user.id % 253) + 2}"

            # Generate PresharedKey if enabled
            try:
                settings = wireguard_service._load_settings()
                if settings.get("wg_preshared_key_enabled", "1") == "1":
                    user.wireguard_preshared_key = wireguard_service.generate_preshared_key()
            except Exception:
                pass

            db.commit()
            db.refresh(user)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate WireGuard keys: {str(e)}")
    
    # Get PresharedKey (safe access)
    psk = getattr(user, 'wireguard_preshared_key', None)

    # Generate config using service (reads all settings from DB)
    try:
        config_content = wireguard_service.generate_client_config(
            client_private_key=user.wireguard_private_key,
            client_ip=user.wireguard_ip,
            preshared_key=psk,
        )
    except Exception as e:
        # Fallback: generate a basic default config
        server_keys = wireguard_service.get_server_keys()
        endpoint_ip = wireguard_service.server_ip
        client_ip = user.wireguard_ip or f"10.66.66.{(user.id % 253) + 2}"
        config_content = f"""[Interface]
PrivateKey = {user.wireguard_private_key}
Address = {client_ip}/24
DNS = 1.1.1.1, 8.8.8.8
MTU = 1380

[Peer]
PublicKey = {server_keys['public_key']}
Endpoint = {endpoint_ip}:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""

    # Generate QR code (non-critical)
    qr_code = None
    try:
        qr_code = wireguard_service.generate_qr_code(config_content)
    except Exception:
        pass
    
    return {
        "filename": f"{user.username}.conf",
        "content": config_content,
        "qr_code": qr_code,
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
