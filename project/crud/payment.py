from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from project.model.payment import Payment, PaymentStatus
from project.model.user import User
from project.core.config import SUBSCRIPTION_PLANS


def create_payment_record(db: Session, user_id: int, plan_id: str) -> Payment:
    if plan_id not in SUBSCRIPTION_PLANS:
        raise ValueError("Invalid subscription plan")

    plan = SUBSCRIPTION_PLANS[plan_id]
    payment = Payment(
        user_id=user_id,
        amount=plan["price"],
        currency="usd",
        plan_id=plan_id,
        status=PaymentStatus.PENDING,
        created_at=datetime.utcnow()
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def update_payment_status(db: Session, stripe_intent_id: str, status: PaymentStatus, failure_reason: str = None):
    """Update payment status based on Stripe webhook event."""
    payment = db.query(Payment).filter(Payment.stripe_payment_intent_id == stripe_intent_id).first()
    if not payment:
        raise ValueError(f"No payment found for intent ID: {stripe_intent_id}")

    payment.status = status
    if status == PaymentStatus.COMPLETED:
        payment.completed_at = datetime.utcnow()
    elif status == PaymentStatus.FAILED:
        payment.failed_at = datetime.utcnow()
        payment.failure_reason = failure_reason
    elif status == PaymentStatus.CANCELED:
        payment.canceled_at = datetime.utcnow()

    db.commit()


def handle_successful_payment(stripe_intent_id: str, db: Session):
    """Handle successful payment: update payment and user subscription."""
    try:
        payment = db.query(Payment).filter(Payment.stripe_payment_intent_id == stripe_intent_id).first()
        if not payment:
            raise ValueError(f"Payment not found for intent {stripe_intent_id}")

        # Update payment status
        update_payment_status(db, stripe_intent_id, PaymentStatus.COMPLETED)

        user = db.query(User).filter(User.id == payment.user_id).first()
        if not user:
            raise ValueError(f"User not found for payment {stripe_intent_id}")

        plan = SUBSCRIPTION_PLANS[payment.plan_id]

        # Extend or set subscription end date
        if user.sub_until and user.sub_until > datetime.utcnow():
            subscription_end = user.sub_until + timedelta(days=30 * plan["duration_months"])
        else:
            subscription_end = datetime.utcnow() + timedelta(days=30 * plan["duration_months"])

        user.is_sub = True
        user.sub_until = subscription_end

        # Reset free attempts only for new subscribers
        if user.free_attempts is None or user.free_attempts <= 0:
            user.free_attempts = 5

        db.commit()
    except Exception as e:
        db.rollback()
        raise e


def get_subscription_plans():
    return {
        "plans": [
            {
                "id": plan_id,
                "name": plan_data["name"],
                "price": plan_data["price"],
                "duration_months": plan_data["duration_months"]
            }
            for plan_id, plan_data in SUBSCRIPTION_PLANS.items()
        ]
    }


def get_user_subscription_status(user: User):
    """Check current user's subscription status."""
    days_remaining = 0
    if user.sub_until and user.is_sub:
        remaining_time = user.sub_until - datetime.utcnow()
        days_remaining = max(0, remaining_time.days)
        if remaining_time.total_seconds() <= 0:
            user.is_sub = False
    return {
        "user_id": user.id,
        "email": user.email,
        "is_subscribed": user.is_sub,
        "subscription_end_date": user.sub_until,
        "days_remaining": days_remaining
    }


def get_user_free_attempts(user: User):
    """Get user's remaining free attempts."""
    return {
        "user_id": user.id,
        "email": user.email,
        "free_attempts": user.free_attempts,
        "is_subscribed": user.is_sub
    }


def use_free_attempt(user: User, db: Session):
    """Decrease user's free attempt count by one."""
    if user.is_sub:
        return {"message": "Unlimited usage for subscribers", "remaining_attempts": "unlimited"}
    if user.free_attempts <= 0:
        raise ValueError("No free attempts remaining")
    user.free_attempts -= 1
    db.commit()
    return {
        "message": "Free attempt used",
        "remaining_attempts": user.free_attempts
    }


def get_user_payment_history(user: User, db: Session):
    """Get user's payment history."""
    payments = db.query(Payment).filter(Payment.user_id == user.id).order_by(Payment.created_at.desc()).all()
    return {
        "payments": [
            {
                "id": p.id,
                "amount": p.amount,
                "currency": p.currency,
                "plan_id": p.plan_id,
                "status": p.status.value,
                "created_at": p.created_at,
                "completed_at": p.completed_at
            }
            for p in payments
        ]
    }