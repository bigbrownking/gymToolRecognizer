import json  # Required for manual decoding
import logging
from typing import List

from fastapi import APIRouter, Query, Depends, HTTPException
from requests import RequestException

import requests
from starlette.responses import JSONResponse

from project.core.config import settings
from project.core.security import get_current_user
from project.model.user import User
from project.schemas.location import GymSearchResponse

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DvGisClient:
    def __init__(self, api_token):
        self.api_token = api_token
        self.base_url = settings.TOGIS_URL

    def find_nearby_gyms(self, latitude, longitude, radius=1000, limit=10):
        url = f"{self.base_url}/3.0/items"

        params = {
            "q": "gym",
            "lat": latitude,
            "lon": longitude,
            "radius": radius,
            "limit": limit,
            "fields": "items.point,items.name,items.address,items.reviews",
            "key": self.api_token
        }

        logger.info(f"Making request to 2Gis API")
        logger.info(f"URL: {url}")
        logger.info(f"Request params: {params}")

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()

            # Explicitly decode as UTF-8 to handle Cyrillic or non-ASCII characters
            data_str = response.content.decode("utf-8")
            data = json.loads(data_str)

            logger.info(f"Received response from 2Gis API")
            logger.info(f"Raw response data: {data}")

            gyms = []

            items = data.get("result", {}).get("items", [])
            logger.info(f"Found {len(items)} results from 2Gis")

            for item in items:
                address_data = item.get("address", {})
                if isinstance(address_data, dict):
                    address_str = ", ".join(f"{k}: {v}" for k, v in address_data.items())
                else:
                    address_str = address_data

                org_rating = item.get("reviews", {}).get("org_rating")
                try:
                    rating_value = float(org_rating) if org_rating else None
                except (TypeError, ValueError):
                    rating_value = None

                gym_info = {
                    "name": item["name"],
                    "address": address_str or "No address available",
                    "coordinates": item["point"],
                    "rating": rating_value,
                }
                gyms.append(gym_info)

            logger.info(f"Processed gyms: {gyms}")
            return gyms

        except RequestException as e:
            logger.error(f"Request failed: {str(e)}", exc_info=True)
            return {"error": str(e)}


router = APIRouter(prefix="/geo", tags=["geo"])

gis_client = DvGisClient(settings.TOGIS_TOKEN)


@router.get(
    "/gyms",
    summary="Search gyms near a location",
    description=(
        "Searches for nearby gyms using 2GIS API based on latitude, longitude, "
        "radius, and result limit. Returns name, address, coordinates, and optional rating."
    ),
    response_model=GymSearchResponse,
    responses={
        200: {
            "description": "List of gyms found or error message",
            "content": {
                "application/json": {
                    "example": {
                        "gyms": [
                            {
                                "name": "FitZone",
                                "address": "улица Ленина, 10",
                                "coordinates": {"lat": 43.115, "lon": 131.885},
                                "rating": 4.5
                            }
                        ],
                        "error": None
                    }
                }
            }
        },
        400: {
            "description": "Consent not given",
            "content": {
                "application/json": {
                    "example": {
                        "gyms": [],
                        "error": "Consent is required"
                    }
                }
            }
        },
        401: {
            "description": "Authentication failed",
            "content": {
                "application/json": {
                    "example": {
                        "gyms": [],
                        "error": "Not authenticated"
                    }
                }
            }
        },
        500: {
            "description": "Unexpected internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "gyms": [],
                        "error": "Internal error or 2GIS API issue"
                    }
                }
            }
        }
    }
)
async def search_gyms(
    current_user: User = Depends(get_current_user),
    lat: float = Query(..., description="Latitude of search center"),
    lon: float = Query(..., description="Longitude of search center"),
    radius: int = Query(1000, ge=100, le=5000, description="Search radius in meters (100-5000)"),
    limit: int = Query(10, ge=1, le=50, description="Number of results to return (1-50)"),
):
    if not current_user.consent_given:
        raise HTTPException(
            status_code=400,
            detail="Consent is required"
        )

    try:
        gyms = gis_client.find_nearby_gyms(
            latitude=lat,
            longitude=lon,
            radius=radius,
            limit=limit
        )

        if isinstance(gyms, dict) and "error" in gyms:
            return JSONResponse(
                content=GymSearchResponse(error=gyms["error"]).dict(),
                media_type="application/json; charset=utf-8"
            )

        return JSONResponse(
            content=GymSearchResponse(gyms=gyms).dict(),
            media_type="application/json; charset=utf-8"
        )

    except Exception as e:
        logger.error(f"Unexpected error during gym search: {str(e)}")
        return JSONResponse(
            content=GymSearchResponse(error="Internal error").dict(),
            media_type="application/json; charset=utf-8"
        )
