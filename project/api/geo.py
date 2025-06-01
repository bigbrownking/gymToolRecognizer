import requests
from fastapi import APIRouter, Query

from project.core.config import settings
from project.schemas.location import GymSearchResponse
import logging

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

            data = response.json()
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

        except requests.exceptions.RequestException as e:
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
        lat: float = Query(description="Latitude of search center"),
        lon: float = Query(description="Longitude of search center"),
        radius: int = Query(1000, ge=100, le=5000, description="Search radius in meters (100-5000)"),
        limit: int = Query(10, ge=1, le=50, description="Number of results to return (1-50)")
):
    try:
        gyms = gis_client.find_nearby_gyms(
            latitude=lat,
            longitude=lon,
            radius=radius,
            limit=limit
        )

        if isinstance(gyms, dict) and "error" in gyms:
            return GymSearchResponse(error=gyms["error"])

        return GymSearchResponse(gyms=gyms)

    except Exception as e:
        return GymSearchResponse(error=str(e))
