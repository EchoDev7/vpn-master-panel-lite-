"""
Users API Endpoints - CRUD operations for VPN users
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
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
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
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
    
    db.delete(user)
    db.commit()
    
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
