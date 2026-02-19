"""
User and Authentication Models
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import enum
import base64

from ..database import Base

# ── Lightweight field-level encryption ──────────────────────────────────────
# Uses Fernet (AES-128-CBC + HMAC-SHA256) from the cryptography library.
# Key is derived from SECRET_KEY so no extra env var is needed.
# Falls back to plaintext only when cryptography is not installed (dev).

def _get_fernet():
    """Return a Fernet cipher keyed from SECRET_KEY."""
    try:
        from cryptography.fernet import Fernet
        import hashlib
        from ..config import settings
        key_bytes = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        return Fernet(fernet_key)
    except Exception:
        return None

def encrypt_field(value: str) -> str:
    """Encrypt a sensitive string field before DB storage."""
    if not value:
        return value
    f = _get_fernet()
    if f is None:
        return value  # fallback: store plain (dev without cryptography)
    return f.encrypt(value.encode()).decode()

def decrypt_field(value: str) -> str:
    """Decrypt a sensitive string field after DB read."""
    if not value:
        return value
    f = _get_fernet()
    if f is None:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except Exception:
        return value  # already plain (migration compat – existing rows)


class UserRole(str, enum.Enum):
    """User roles with permissions hierarchy"""
    SUPER_ADMIN = "super_admin"  # Full access
    ADMIN = "admin"              # Can manage users and servers
    RESELLER = "reseller"        # Can create limited users
    USER = "user"                # End user


class UserStatus(str, enum.Enum):
    """User account status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    DISABLED = "disabled"


class TrafficType(str, enum.Enum):
    """Traffic type for monitoring"""
    DIRECT = "direct"      # Direct VPN connection
    TUNNEL = "tunnel"      # Through Iran-Foreign tunnel


class User(Base):
    """User model for authentication and VPN access"""
    __tablename__ = "users"
    
    # Identity
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255))
    phone = Column(String(20))
    
    # Role & Status
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    
    # Limits
    data_limit_gb = Column(Float, default=0)  # 0 = unlimited
    connection_limit = Column(Integer, default=1)
    speed_limit_mbps = Column(Float, default=0) # F7 Bandwidth Shaping
    expiry_date = Column(DateTime(timezone=True))
    
    # Usage Tracking
    total_upload_bytes = Column(Integer, default=0)
    total_download_bytes = Column(Integer, default=0)
    last_connection = Column(DateTime(timezone=True))
    
    # Reseller Specific
    reseller_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    max_users = Column(Integer, default=0)  # For resellers
    max_data_gb = Column(Float, default=0)  # Total data quota for reseller
    
    # VPN Credentials
    openvpn_enabled = Column(Boolean, default=True)
    wireguard_enabled = Column(Boolean, default=True)
    l2tp_enabled = Column(Boolean, default=True)
    _l2tp_password = Column("l2tp_password", String(512))  # stored encrypted
    cisco_enabled = Column(Boolean, default=True)
    _cisco_password = Column("cisco_password", String(512))  # stored encrypted

    # WireGuard Specific
    wireguard_public_key = Column(String(255))
    _wireguard_private_key = Column("wireguard_private_key", String(512))  # stored encrypted
    wireguard_ip = Column(String(50))
    _wireguard_preshared_key = Column("wireguard_preshared_key", String(512))  # stored encrypted

    # ── Transparent encrypt/decrypt via Python properties ────────────────────
    @property
    def l2tp_password(self) -> str:
        return decrypt_field(self._l2tp_password)

    @l2tp_password.setter
    def l2tp_password(self, value: str):
        self._l2tp_password = encrypt_field(value)

    @property
    def cisco_password(self) -> str:
        return decrypt_field(self._cisco_password)

    @cisco_password.setter
    def cisco_password(self, value: str):
        self._cisco_password = encrypt_field(value)

    @property
    def wireguard_private_key(self) -> str:
        return decrypt_field(self._wireguard_private_key)

    @wireguard_private_key.setter
    def wireguard_private_key(self, value: str):
        self._wireguard_private_key = encrypt_field(value)

    @property
    def wireguard_preshared_key(self) -> str:
        return decrypt_field(self._wireguard_preshared_key)

    @wireguard_preshared_key.setter
    def wireguard_preshared_key(self, value: str):
        self._wireguard_preshared_key = encrypt_field(value)
    
    # Subscription
    subscription_token = Column(String(100), unique=True, index=True, nullable=True)
    
    # Metadata
    # These columns are moved to a new # Timestamps section below
    # created_at = Column(DateTime(timezone=True), server_default=func.now())
    # updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    reseller = relationship("User", remote_side=[id], foreign_keys=[reseller_id])
    sub_users = relationship("User", back_populates="reseller", foreign_keys=[reseller_id])
    traffic_logs = relationship("TrafficLog", back_populates="user", cascade="all, delete-orphan")
    connection_logs = relationship("ConnectionLog", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("UserSubscription", back_populates="user", cascade="all, delete-orphan")
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime)
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if user is active and not expired"""
        if self.status != UserStatus.ACTIVE:
            return False
        if self.expiry_date and datetime.utcnow() > self.expiry_date:
            return False
        return True
    
    @property
    def data_usage_gb(self) -> float:
        """Total data usage in GB"""
        upload = self.total_upload_bytes or 0
        download = self.total_download_bytes or 0
        return (upload + download) / (1024**3)
    
    @property
    def has_data_remaining(self) -> bool:
        """Check if user has data quota remaining"""
        limit = self.data_limit_gb or 0
        if limit == 0:  # Unlimited
            return True
        return self.data_usage_gb < limit
    
    @property
    def total_traffic_gb(self) -> float:
        """Get total traffic in GB"""
        total_bytes = self.total_upload_bytes + self.total_download_bytes
        return round(total_bytes / (1024**3), 2)

    @property
    def is_online(self) -> bool:
        """Check if user has been active in the last 3 minutes"""
        if not self.last_connection:
            return False
        # Use UTC for comparison
        return datetime.utcnow() - self.last_connection < timedelta(minutes=3)


class TrafficLog(Base):
    """Traffic log for detailed usage tracking"""
    __tablename__ = "traffic_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Traffic details
    upload_bytes = Column(Integer, default=0)
    download_bytes = Column(Integer, default=0)
    traffic_type = Column(Enum(TrafficType), default=TrafficType.DIRECT)
    tunnel_id = Column(Integer, ForeignKey("tunnels.id"), nullable=True)
    
    # Timestamp
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="traffic_logs")
    
    def __repr__(self):
        return f"<TrafficLog(user_id={self.user_id}, type='{self.traffic_type}')>"


class ConnectionLog(Base):
    """Connection log for tracking user sessions"""
    __tablename__ = "connection_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    protocol = Column(String(20))  # openvpn, wireguard, l2tp, cisco
    server_id = Column(Integer, ForeignKey("vpn_servers.id"))
    
    # Connection details
    client_ip = Column(String(50))
    server_ip = Column(String(50))
    port = Column(Integer)
    
    # Session tracking
    connected_at = Column(DateTime(timezone=True), server_default=func.now())
    disconnected_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    
    # Traffic
    upload_bytes = Column(Integer, default=0)
    download_bytes = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="connection_logs")
    
    def __repr__(self):
        return f"<ConnectionLog(user_id={self.user_id}, protocol='{self.protocol}')>"


class Notification(Base):
    """Notification model for system alerts"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # None = system-wide
    
    # Notification details
    type = Column(String(20), nullable=False)  # success, info, warning, error
    title = Column(String(255), nullable=False)
    message = Column(String(1000), nullable=False)
    
    # Status
    read = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<Notification(title='{self.title}', type='{self.type}')>"


class ActivityLog(Base):
    """Activity log for audit trail"""
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Activity details
    type = Column(String(50), nullable=False)  # user_created, user_deleted, login, etc.
    description = Column(String(500), nullable=False)
    
    # Context
    ip_address = Column(String(50))
    user_agent = Column(String(255))
    meta_data = Column(String(1000))  # JSON string for additional data (renamed from metadata)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<ActivityLog(type='{self.type}', user_id={self.user_id})>"

