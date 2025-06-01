from typing import List, Optional

from pydantic import BaseModel


class LocationRequest(BaseModel):
    latitude: float
    longitude: float


class GymLocation(BaseModel):
    name: str
    address: str
    coordinates: dict
    rating: Optional[float] = None


class GymSearchResponse(BaseModel):
    gyms: List[GymLocation] = []
    error: Optional[str] = None
