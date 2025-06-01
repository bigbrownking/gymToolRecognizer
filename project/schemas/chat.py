from datetime import datetime

from pydantic import BaseModel


class WorkoutGenerateResponse(BaseModel):
    id: int
    user_id: int
    goal: str
    plan: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    id: int
    user_id: int
    goal: str
    plan: str
    created_at: datetime
