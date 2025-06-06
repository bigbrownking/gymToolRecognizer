import stripe
from fastapi import APIRouter, Depends, Request, HTTPException, Header
from sqlalchemy.orm import Session

from project.core.config import SUBSCRIPTION_PLANS, settings
from project.core.database import get_db
from project.core.security import get_current_user
from project.schemas.payment import PaymentRequest
from project.crud.payment import (
    create_payment_record,
    handle_successful_payment,
    get_subscription_plans,
    get_user_subscription_status,
    get_user_free_attempts,
    use_free_attempt,
    get_user_payment_history, update_payment_status
)
from project.model.payment import PaymentStatus

stripe.api_key = settings.STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET

router = APIRouter(prefix="/payment", tags=["payment"])


@router.post("/create-payment-intent/")
def create_payment_intent(
    payment_request: PaymentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        payment = create_payment_record(db, current_user.id, payment_request.plan_id)
        plan = payment_request.plan_id
        amount_cents = int(SUBSCRIPTION_PLANS[plan]["price"] * 100)

        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            payment_method_types=["card"],
            metadata={
                "user_id": str(current_user.id),
                "payment_id": str(payment.id),
                "plan_id": plan,
                "user_email": current_user.email
            },
            description=f"Subscription: {SUBSCRIPTION_PLANS[plan]['name']} for {current_user.email}",
            receipt_email=current_user.email
        )

        payment.stripe_payment_intent_id = intent.id
        db.commit()

        return {
            "client_secret": intent.client_secret,
            "payment_id": payment.id,
            "amount": amount_cents,
            "currency": "usd"
        }

    except stripe.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/webhook/")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db)
):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature or payload")

    try:
        if event['type'] == 'payment_intent.succeeded':
            await handle_successful_payment(event['data']['object'].id, db)
        elif event['type'] in ['payment_intent.payment_failed', 'payment_intent.canceled']:
            status_map = {
                'payment_intent.payment_failed': PaymentStatus.FAILED,
                'payment_intent.canceled': PaymentStatus.CANCELED
            }
            reason = event['data']['object'].get('last_payment_error', {}).get('message')
            update_payment_status(db, event['data']['object'].id, status_map[event['type']], reason)
        else:
            return {"status": "ignored"}
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


@router.get("/plans/")
def get_plans():
    return get_subscription_plans()


@router.get("/check_subscription/")
def check_subscription(current_user: dict = Depends(get_current_user)):
    return get_user_subscription_status(current_user)


@router.get("/get_free_attempts/")
def get_free_attempts(current_user: dict = Depends(get_current_user)):
    return get_user_free_attempts(current_user)


@router.post("/use_free_attempt/")
def use_free_attempt_route(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return use_free_attempt(current_user, db)


@router.get("/payment_history/")
def get_payment_history_route(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_user_payment_history(current_user, db)
