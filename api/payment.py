import stripe
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from schemas.payment import PaymentRequest
from model.user import User

router = APIRouter(prefix="/payment", tags=["payment"])


@router.post(
    "/create-payment-intent/",
    summary="Create Stripe payment intent",
    description="Creates a Stripe payment intent for the specified user and marks them as subscribed.",
    responses={
        200: {
            "description": "Payment intent created and user marked as subscribed",
            "content": {
                "application/json": {
                    "example": {
                        "client_secret": "pi_1ExAmPlEsEcReT",
                        "message": "Payment initiated, user marked as subscribed"
                    }
                }
            },
        },
        404: {"description": "User not found"},
        500: {"description": "Stripe error or internal failure"},
    }
)
def create_payment_intent(
    payment: PaymentRequest,
    db: Session = Depends(get_db)
):
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(payment.amount * 100),
            currency="usd",
            payment_method_types=["card"],
            metadata={"user_id": str(payment.user_id)},  # Add user ID here
        )

        # OPTIONAL: You might want to wait for actual payment confirmation using Stripe webhooks
        # For now, we assume payment is successful here
        user = db.query(User).filter(User.id == payment.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.is_sub = True
        db.commit()
        db.refresh(user)

        return {"client_secret": intent.client_secret, "message": "Payment initiated, user marked as subscribed"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/check_subscription",
    summary="Check user subscription status",
    description="Returns whether the current authenticated user is subscribed.",
    responses={
        200: {
            "description": "Subscription status returned",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": 1,
                        "email": "user@example.com",
                        "is_subscribed": True
                    }
                }
            }
        },
        401: {"description": "Unauthorized"},
    }
)
def check_subscription(current_user: User = Depends(get_current_user)):
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "is_subscribed": current_user.is_sub
    }


@router.get(
    "/get_free_attempts",
    summary="Get user's remaining free attempts",
    description="Returns how many free attempts the authenticated user has left.",
    responses={
        200: {
            "description": "Free attempt count returned",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": 1,
                        "email": "user@example.com",
                        "free_attempts": 3
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
        "free_attempts": current_user.free_attempts
    }