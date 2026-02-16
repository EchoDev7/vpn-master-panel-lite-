"""
Subscription Models
User subscription and payment management
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .user import Base


class SubscriptionPlan(Base):
    """Subscription plans table"""
    __tablename__ = "subscription_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    price = Column(Float, default=0.0)
    duration_days = Column(Integer, default=30)
    traffic_limit_gb = Column(Integer, default=10)  # GB, 0 = unlimited
    connection_limit = Column(Integer, default=3)  # Max simultaneous connections
    max_devices = Column(Integer, default=5)
    features = Column(Text)  # JSON string of features
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("UserSubscription", back_populates="plan")


class PaymentStatus(str, enum.Enum):
    """Payment status enum"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class UserSubscription(Base):
    """User subscriptions table"""
    __tablename__ = "user_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    
    # Subscription details
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    auto_renew = Column(Boolean, default=False)
    
    # Usage tracking
    traffic_used_gb = Column(Float, default=0.0)
    traffic_limit_gb = Column(Integer)  # Copied from plan
    connection_limit = Column(Integer)  # Copied from plan
    
    # Payment info
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_method = Column(String(50))  # stripe, paypal, crypto, etc.
    payment_id = Column(String(255))  # External payment ID
    amount_paid = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    
    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    history = relationship("SubscriptionHistory", back_populates="subscription")


class SubscriptionHistory(Base):
    """Subscription payment history"""
    __tablename__ = "subscription_history"
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Payment details
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    payment_method = Column(String(50))
    payment_id = Column(String(255))
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Transaction info
    transaction_date = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)
    meta_data = Column(Text)  # JSON metadata
    
    # Relationships
    subscription = relationship("UserSubscription", back_populates="history")
    user = relationship("User")
