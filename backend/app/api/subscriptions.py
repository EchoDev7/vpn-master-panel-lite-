"""
Subscription API Endpoints
Manage subscription plans and user subscriptions
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import logging

from ..database import get_db
from ..models.subscription import SubscriptionPlan, UserSubscription, SubscriptionHistory, PaymentStatus
from ..models.user import User
from ..utils.security import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================
# Subscription Plans
# ============================================

@router.get("/subscription-plans")
async def get_subscription_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all active subscription plans"""
    try:
        plans = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.is_active == True
        ).order_by(SubscriptionPlan.sort_order).all()
        
        return {
            "plans": [
                {
                    "id": plan.id,
                    "name": plan.name,
                    "description": plan.description,
                    "price": plan.price,
                    "duration_days": plan.duration_days,
                    "traffic_limit_gb": plan.traffic_limit_gb,
                    "connection_limit": plan.connection_limit,
                    "max_devices": plan.max_devices,
                    "features": plan.features
                }
                for plan in plans
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching subscription plans: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription plans")


@router.get("/subscription-plans/{plan_id}")
async def get_subscription_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific subscription plan"""
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return {
        "id": plan.id,
        "name": plan.name,
        "description": plan.description,
        "price": plan.price,
        "duration_days": plan.duration_days,
        "traffic_limit_gb": plan.traffic_limit_gb,
        "connection_limit": plan.connection_limit,
        "max_devices": plan.max_devices,
        "features": plan.features
    }


# ============================================
# User Subscriptions
# ============================================

@router.get("/my-subscription")
async def get_my_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's active subscription"""
    try:
        subscription = db.query(UserSubscription).filter(
            UserSubscription.user_id == current_user.id,
            UserSubscription.is_active == True,
            UserSubscription.end_date > datetime.utcnow()
        ).first()
        
        if not subscription:
            return {"subscription": None, "message": "No active subscription"}
        
        # Calculate days remaining
        days_remaining = (subscription.end_date - datetime.utcnow()).days
        
        # Calculate usage percentage
        usage_percent = 0
        if subscription.traffic_limit_gb > 0:
            usage_percent = (subscription.traffic_used_gb / subscription.traffic_limit_gb) * 100
        
        return {
            "subscription": {
                "id": subscription.id,
                "plan_name": subscription.plan.name,
                "start_date": subscription.start_date.isoformat(),
                "end_date": subscription.end_date.isoformat(),
                "days_remaining": days_remaining,
                "traffic_used_gb": subscription.traffic_used_gb,
                "traffic_limit_gb": subscription.traffic_limit_gb,
                "usage_percent": round(usage_percent, 2),
                "connection_limit": subscription.connection_limit,
                "auto_renew": subscription.auto_renew,
                "payment_status": subscription.payment_status.value
            }
        }
    except Exception as e:
        logger.error(f"Error fetching user subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription")


@router.post("/subscribe/{plan_id}")
async def subscribe_to_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Subscribe to a plan"""
    try:
        # Get plan
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Check if user already has an active subscription
        existing = db.query(UserSubscription).filter(
            UserSubscription.user_id == current_user.id,
            UserSubscription.is_active == True,
            UserSubscription.end_date > datetime.utcnow()
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="You already have an active subscription")
        
        # Create new subscription
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=plan.duration_days)
        
        subscription = UserSubscription(
            user_id=current_user.id,
            plan_id=plan.id,
            start_date=start_date,
            end_date=end_date,
            traffic_limit_gb=plan.traffic_limit_gb,
            connection_limit=plan.connection_limit,
            payment_status=PaymentStatus.PENDING if plan.price > 0 else PaymentStatus.COMPLETED,
            amount_paid=plan.price
        )
        
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        # Create history record
        history = SubscriptionHistory(
            subscription_id=subscription.id,
            user_id=current_user.id,
            amount=plan.price,
            payment_status=subscription.payment_status,
            description=f"Subscribed to {plan.name} plan"
        )
        db.add(history)
        db.commit()
        
        return {
            "message": "Subscription created successfully",
            "subscription_id": subscription.id,
            "payment_required": plan.price > 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create subscription")


@router.post("/cancel-subscription")
async def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel current subscription"""
    try:
        subscription = db.query(UserSubscription).filter(
            UserSubscription.user_id == current_user.id,
            UserSubscription.is_active == True
        ).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        subscription.is_active = False
        subscription.auto_renew = False
        db.commit()
        
        return {"message": "Subscription cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.get("/subscription-history")
async def get_subscription_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's subscription history"""
    try:
        history = db.query(SubscriptionHistory).filter(
            SubscriptionHistory.user_id == current_user.id
        ).order_by(SubscriptionHistory.transaction_date.desc()).all()
        
        return {
            "history": [
                {
                    "id": h.id,
                    "amount": h.amount,
                    "currency": h.currency,
                    "payment_method": h.payment_method,
                    "payment_status": h.payment_status.value,
                    "transaction_date": h.transaction_date.isoformat(),
                    "description": h.description
                }
                for h in history
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching subscription history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch history")


# ============================================
# Admin Endpoints
# ============================================

@router.post("/admin/plans", dependencies=[Depends(get_current_user)])
async def create_plan(
    name: str,
    description: str,
    price: float,
    duration_days: int,
    traffic_limit_gb: int,
    connection_limit: int,
    max_devices: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new subscription plan (Admin only)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        plan = SubscriptionPlan(
            name=name,
            description=description,
            price=price,
            duration_days=duration_days,
            traffic_limit_gb=traffic_limit_gb,
            connection_limit=connection_limit,
            max_devices=max_devices
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        
        return {"message": "Plan created successfully", "plan_id": plan.id}
    except Exception as e:
        logger.error(f"Error creating plan: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create plan")
