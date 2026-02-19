"""
Authentication API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import timedelta

from ..database import get_db
from ..models.user import User, UserRole
from ..utils.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
    blacklist_token,
    check_rate_limit,
    security as bearer_scheme,
)
from ..config import settings

router = APIRouter()


# Request/Response Models
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    role: str
    full_name: Optional[str]
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login endpoint - authenticate user and return JWT tokens.
    Rate-limited to 10 attempts per minute per IP.
    """
    # Rate limiting by client IP
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    # Find user
    user = db.query(User).filter(User.username == login_data.username).first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or expired"
        )

    # Create tokens
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information
    """
    return current_user


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
):
    """
    Logout endpoint - blacklists the current access token so it can no longer be used.
    """
    blacklist_token(credentials.credentials)
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    from ..utils.security import decode_token
    
    try:
        payload = decode_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        username = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new tokens
        new_access_token = create_access_token(
            data={"sub": user.username, "role": user.role.value}
        )
        new_refresh_token = create_refresh_token(
            data={"sub": user.username}
        )
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
