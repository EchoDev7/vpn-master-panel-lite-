"""
User and Authentication Models
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import enum

from ..database import Base


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
    l2tp_password = Column(String(255))  # Separate password for L2TP
    cisco_enabled = Column(Boolean, default=True)
    cisco_password = Column(String(255))  # Separate password for Cisco
    
    # WireGuard Specific
    wireguard_public_key = Column(String(255))
    wireguard_private_key = Column(String(255))
    wireguard_ip = Column(String(50))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    reseller = relationship("User", remote_side=[id], foreign_keys=[reseller_id])
    sub_users = relationship("User", back_populates="reseller", foreign_keys=[reseller_id])
    traffic_logs = relationship("TrafficLog", back_populates="user")
    connection_logs = relationship("ConnectionLog", back_populates="user")
    
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


class TrafficLog(Base):
    """Log VPN traffic for users"""
    __tablename__ = "traffic_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Traffic data
    upload_bytes = Column(Integer, default=0)
    download_bytes = Column(Integer, default=0)
    
    # Session info
    protocol = Column(String(20))  # openvpn, wireguard, l2tp, cisco
    server_id = Column(Integer, ForeignKey("vpn_servers.id"))
    
    # Timestamps
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="traffic_logs")
    
    def __repr__(self):
        return f"<TrafficLog(user_id={self.user_id}, up={self.upload_bytes}, down={self.download_bytes})>"


class ConnectionLog(Base):
    """Log VPN connections"""
    __tablename__ = "connection_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Connection details
    protocol = Column(String(20))
    server_id = Column(Integer, ForeignKey("vpn_servers.id"))
    client_ip = Column(String(50))
    virtual_ip = Column(String(50))
    
    # Status
    connected_at = Column(DateTime(timezone=True), server_default=func.now())
    disconnected_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="connection_logs")
    
    def __repr__(self):
        return f"<ConnectionLog(user_id={self.user_id}, protocol={self.protocol}, active={self.is_active})>"
