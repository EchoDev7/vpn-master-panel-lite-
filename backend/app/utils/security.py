"""
Authentication and Security Utilities
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import time
import threading

from ..config import settings
from ..database import get_db
from ..models.user import User, UserRole

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer token
security = HTTPBearer()

# ─── Token Blacklist (in-memory, thread-safe) ───────────────────────────────
_blacklist_lock = threading.Lock()
_token_blacklist: dict[str, float] = {}  # token_jti -> expiry_timestamp

def _cleanup_blacklist():
    """Remove expired tokens from blacklist."""
    now = time.time()
    with _blacklist_lock:
        expired = [k for k, v in _token_blacklist.items() if v < now]
        for k in expired:
            del _token_blacklist[k]

def blacklist_token(token: str):
    """Add a token to the blacklist until it expires."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp = payload.get("exp", 0)
        jti = payload.get("jti") or token[-32:]  # use last 32 chars as fallback id
        _cleanup_blacklist()
        with _blacklist_lock:
            _token_blacklist[jti] = float(exp)
    except Exception:
        pass

def is_token_blacklisted(token: str) -> bool:
    """Check if a token has been blacklisted."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti") or token[-32:]
        with _blacklist_lock:
            return jti in _token_blacklist
    except Exception:
        return False

# ─── Rate Limiter (in-memory, per-IP) ────────────────────────────────────────
_rate_lock = threading.Lock()
_login_attempts: dict[str, list[float]] = {}  # ip -> [timestamps]

RATE_LIMIT_WINDOW = 60   # seconds
RATE_LIMIT_MAX    = 10   # max attempts per window

def check_rate_limit(ip: str):
    """Raise 429 if IP exceeded login attempts."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    with _rate_lock:
        attempts = [t for t in _login_attempts.get(ip, []) if t > window_start]
        attempts.append(now)
        _login_attempts[ip] = attempts
        if len(attempts) > RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=429,
                detail=f"Too many login attempts. Try again in {RATE_LIMIT_WINDOW} seconds.",
                headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
            )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token with Unix timestamp exp claim."""
    import calendar
    to_encode = data.copy()

    if expires_delta:
        expire_dt = datetime.now(timezone.utc) + expires_delta
    else:
        expire_dt = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Store exp as Unix timestamp (int) — required by RFC 7519
    to_encode.update({"exp": calendar.timegm(expire_dt.utctimetuple())})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token with Unix timestamp exp claim."""
    import calendar
    to_encode = data.copy()
    expire_dt = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": calendar.timegm(expire_dt.utctimetuple()),
        "type": "refresh",
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials

    # Reject blacklisted (logged-out) tokens
    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)

    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or expired"
        )

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require admin or super admin role"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def get_current_super_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require super admin role"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )
    return current_user


def create_initial_admin():
    """Create initial admin user if not exists"""
    from ..database import get_db_context
    
    with get_db_context() as db:
        # Check if any super admin exists
        admin_exists = db.query(User).filter(
            User.role == UserRole.SUPER_ADMIN
        ).first()
        
        if not admin_exists:
            # Create initial admin
            admin = User(
                username=settings.INITIAL_ADMIN_USERNAME,
                email=settings.INITIAL_ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.INITIAL_ADMIN_PASSWORD),
                role=UserRole.SUPER_ADMIN,
                full_name="Super Administrator"
            )
            db.add(admin)
            db.commit()
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"✅ Initial admin user created: {settings.INITIAL_ADMIN_USERNAME}")


# --- F10 Fix: Missing Dependencies for connections.py ---

async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    return await get_current_user(credentials, db)


async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user
