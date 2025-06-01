import stripe
import json
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from sqlalchemy.orm import Session
from typing import Optional

from project.core.config import settings
from project.core.database import get_db
from project.core.security import get_current_user
from project.schemas.payment import PaymentRequest, SubscriptionPlan
from project.model.user import User
from project.model.payment import Payment, PaymentStatus

router = APIRouter(prefix="/payment", tags=["payment"])

stripe.api_key = settings.STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET

SUBSCRIPTION_PLANS = {
    "monthly": {
        "price": 0.01,
        "duration_months": 1,
        "name": "Basic Monthly"
    },
    "yearly": {
        "price": 99.99,
        "duration_months": 12,
        "name": "Yearly Plan"
    }
}

logger = logging.getLogger(__name__)


@router.post(
    "/create-payment-intent/",
    summary="Create Stripe payment intent",
    description="Creates a Stripe payment intent for subscription payment",
    responses={
        200: {
            "description": "Payment intent created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "client_secret": "pi_1ExAmPlEsEcReT",
                        "payment_id": "payment_123",
                        "amount": 999,
                        "currency": "usd"
                    }
                }
            },
        },
        400: {"description": "Invalid payment request"},
        404: {"description": "User not found"},
        500: {"description": "Payment processing error"},
    }
)
def create_payment_intent(
        payment_request: PaymentRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    try:
        # Validate subscription plan
        if payment_request.plan_id not in SUBSCRIPTION_PLANS:
            raise HTTPException(status_code=400, detail="Invalid subscription plan")

        plan = SUBSCRIPTION_PLANS[payment_request.plan_id]
        amount_cents = int(plan["price"] * 100)

        # Create payment record in database
        payment_record = Payment(
            user_id=current_user.id,
            amount=plan["price"],
            currency="usd",
            plan_id=payment_request.plan_id,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow()
        )
        db.add(payment_record)
        db.commit()
        db.refresh(payment_record)

        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            payment_method_types=["card"],
            metadata={
                "user_id": str(current_user.id),
                "payment_id": str(payment_record.id),
                "plan_id": payment_request.plan_id,
                "user_email": current_user.email
            },
            description=f"Subscription: {plan['name']} for {current_user.email}",
            receipt_email=current_user.email
        )

        payment_record.stripe_payment_intent_id = intent.id
        db.commit()

        return {
            "client_secret": intent.client_secret,
            "payment_id": payment_record.id,
            "amount": amount_cents,
            "currency": "usd"
        }

    except stripe.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment processing error: {str(e)}")
    except Exception as e:
        logger.error(f"Payment intent creation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/webhook/",
    summary="Stripe webhook handler",
    description="Handles Stripe webhook events for payment confirmation",
    responses={
        200: {"description": "Webhook processed successfully"},
        400: {"description": "Invalid webhook signature or payload"},
        500: {"description": "Webhook processing error"},
    }
)
async def stripe_webhook(
        request: Request,
        stripe_signature: str = Header(None, alias="stripe-signature"),
        db: Session = Depends(get_db)
):
    payload = await request.body()

    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.error("Invalid payload in webhook")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        logger.error("Invalid signature in webhook")
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        # Handle the event
        if event['type'] == 'payment_intent.succeeded':
            await handle_payment_success(event['data']['object'], db)
        elif event['type'] == 'payment_intent.payment_failed':
            await handle_payment_failure(event['data']['object'], db)
        elif event['type'] == 'payment_intent.canceled':
            await handle_payment_canceled(event['data']['object'], db)
        else:
            logger.info(f"Unhandled event type: {event['type']}")

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


async def handle_payment_success(payment_intent, db: Session):
    """Handle successful payment"""
    try:
        stripe_intent_id = payment_intent['id']
        metadata = payment_intent['metadata']

        # Find payment record
        payment_record = db.query(Payment).filter(
            Payment.stripe_payment_intent_id == stripe_intent_id
        ).first()

        if not payment_record:
            logger.error(f"Payment record not found for intent: {stripe_intent_id}")
            return

        # Update payment status
        payment_record.status = PaymentStatus.COMPLETED
        payment_record.completed_at = datetime.utcnow()

        # Update user subscription
        user = db.query(User).filter(User.id == payment_record.user_id).first()
        if user:
            plan = SUBSCRIPTION_PLANS[payment_record.plan_id]

            # Calculate subscription end date
            if user.sub_until and user.sub_until > datetime.utcnow():
                # Extend existing subscription
                subscription_end = user.sub_until + timedelta(days=30 * plan["duration_months"])
            else:
                # New subscription
                subscription_end = datetime.utcnow() + timedelta(days=30 * plan["duration_months"])

            user.is_sub = True
            user.sub_until = subscription_end

            # Reset free attempts for new subscribers (if they had no subscription before)
            if user.free_attempts is None or user.free_attempts <= 0:
                user.free_attempts = 5  # Reset to default for new subscribers

        db.commit()
        logger.info(f"Payment successful for user {user.id if user else 'unknown'}")

    except Exception as e:
        logger.error(f"Error handling payment success: {str(e)}")
        db.rollback()


async def handle_payment_failure(payment_intent, db: Session):
    """Handle failed payment"""
    try:
        stripe_intent_id = payment_intent['id']

        payment_record = db.query(Payment).filter(
            Payment.stripe_payment_intent_id == stripe_intent_id
        ).first()

        if payment_record:
            payment_record.status = PaymentStatus.FAILED
            payment_record.failed_at = datetime.utcnow()
            payment_record.failure_reason = payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')
            db.commit()

        logger.info(f"Payment failed for intent: {stripe_intent_id}")

    except Exception as e:
        logger.error(f"Error handling payment failure: {str(e)}")
        db.rollback()


async def handle_payment_canceled(payment_intent, db: Session):
    """Handle canceled payment"""
    try:
        stripe_intent_id = payment_intent['id']

        payment_record = db.query(Payment).filter(
            Payment.stripe_payment_intent_id == stripe_intent_id
        ).first()

        if payment_record:
            payment_record.status = PaymentStatus.CANCELED
            payment_record.canceled_at = datetime.utcnow()
            db.commit()

        logger.info(f"Payment canceled for intent: {stripe_intent_id}")

    except Exception as e:
        logger.error(f"Error handling payment cancellation: {str(e)}")
        db.rollback()


@router.get(
    "/plans/",
    summary="Get available subscription plans",
    description="Returns all available subscription plans with pricing",
    responses={
        200: {
            "description": "Available subscription plans",
            "content": {
                "application/json": {
                    "example": {
                        "plans": [
                            {
                                "id": "basic",
                                "name": "Basic Monthly",
                                "price": 9.99,
                                "duration_months": 1
                            }
                        ]
                    }
                }
            }
        }
    }
)
def get_subscription_plans():
    plans = []
    for plan_id, plan_data in SUBSCRIPTION_PLANS.items():
        plans.append({
            "id": plan_id,
            "name": plan_data["name"],
            "price": plan_data["price"],
            "duration_months": plan_data["duration_months"]
        })
    return {"plans": plans}


@router.get(
    "/check_subscription/",
    summary="Check user subscription status",
    description="Returns detailed subscription information for the current user",
    responses={
        200: {
            "description": "Subscription status returned",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": 1,
                        "email": "user@example.com",
                        "is_subscribed": True,
                        "subscription_end_date": "2024-03-15T10:30:00Z",
                        "days_remaining": 15
                    }
                }
            }
        },
        401: {"description": "Unauthorized"},
    }
)
def check_subscription(current_user: User = Depends(get_current_user)):
    days_remaining = 0
    if current_user.sub_until and current_user.is_sub:
        remaining_time = current_user.sub_until - datetime.utcnow()
        days_remaining = max(0, remaining_time.days)

        # Check if subscription has expired
        if remaining_time.total_seconds() <= 0:
            current_user.is_sub = False

    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "is_subscribed": current_user.is_sub,
        "subscription_end_date": current_user.sub_until,
        "days_remaining": days_remaining
    }


@router.get(
    "/get_free_attempts/",
    summary="Get user's remaining free attempts",
    description="Returns how many free attempts the authenticated user has left",
    responses={
        200: {
            "description": "Free attempt count returned",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": 1,
                        "email": "user@example.com",
                        "free_attempts": 3,
                        "is_subscribed": False
                    }
                }
            }
        },
        401: {"description": "Unauthorized"},
    }
)
def get_free_attempts(current_user: User = Depends(get_current_user)):
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "free_attempts": current_user.free_attempts,
        "is_subscribed": current_user.is_sub
    }


@router.post(
    "/use_free_attempt/",
    summary="Use one free attempt",
    description="Decrements the user's free attempt count by one",
    responses={
        200: {
            "description": "Free attempt used successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Free attempt used",
                        "remaining_attempts": 2
                    }
                }
            }
        },
        400: {"description": "No free attempts remaining"},
        401: {"description": "Unauthorized"},
    }
)
def use_free_attempt(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    if current_user.is_sub:
        return {"message": "Unlimited usage for subscribers", "remaining_attempts": "unlimited"}

    if current_user.free_attempts <= 0:
        raise HTTPException(status_code=400, detail="No free attempts remaining")

    current_user.free_attempts -= 1
    db.commit()

    return {
        "message": "Free attempt used",
        "remaining_attempts": current_user.free_attempts
    }


@router.get(
    "/payment_history/",
    summary="Get user's payment history",
    description="Returns the payment history for the authenticated user",
    responses={
        200: {
            "description": "Payment history returned",
            "content": {
                "application/json": {
                    "example": {
                        "payments": [
                            {
                                "id": 1,
                                "amount": 9.99,
                                "currency": "usd",
                                "plan_id": "basic",
                                "status": "completed",
                                "created_at": "2024-02-15T10:30:00Z"
                            }
                        ]
                    }
                }
            }
        },
        401: {"description": "Unauthorized"},
    }
)
def get_payment_history(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    payments = db.query(Payment).filter(
        Payment.user_id == current_user.id
    ).order_by(Payment.created_at.desc()).all()

    payment_history = []
    for payment in payments:
        payment_history.append({
            "id": payment.id,
            "amount": payment.amount,
            "currency": payment.currency,
            "plan_id": payment.plan_id,
            "status": payment.status.value,
            "created_at": payment.created_at,
            "completed_at": payment.completed_at
        })

    return {"payments": payment_history}
