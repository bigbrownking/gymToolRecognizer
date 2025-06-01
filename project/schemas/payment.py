# project/schemas/payment.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class SubscriptionPlan(str, Enum):
    BASIC = "basic"
    PREMIUM = "premium"
    YEARLY = "yearly"


class PaymentRequest(BaseModel):
    plan_id: SubscriptionPlan = Field(..., description="Subscription plan ID")

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class PaymentResponse(BaseModel):
    client_secret: str
    payment_id: int
    amount: int
    currency: str


class SubscriptionStatus(BaseModel):
    user_id: int
    email: str
    is_subscribed: bool
    subscription_end_date: Optional[datetime] = None
    days_remaining: int = 0


class FreeAttempts(BaseModel):
    user_id: int
    email: str
    free_attempts: int
    is_subscribed: bool


class PaymentHistory(BaseModel):
    id: int
    amount: float
    currency: str
    plan_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class SubscriptionPlanInfo(BaseModel):
    id: str
    name: str
    price: float
    duration_months: int
