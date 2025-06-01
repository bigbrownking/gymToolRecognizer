from typing import Optional

from pydantic import BaseModel
from datetime import date


class GymLogRequest(BaseModel):
    date: date
    went: bool
    action: Optional[str] = None
