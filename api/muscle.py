from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
import time

from starlette.responses import StreamingResponse

from core.config import settings
from core.database import get_db, upload_image_to_minio
from model.muscle import Muscle
import requests
import os
from io import BytesIO

RAPIDAPI_KEY = os.getenv("RAPID_KEY")
RAPIDAPI_HOST = os.getenv("RAPID_HOST")
multiColorUrl = os.getenv("DUAL_COLOR")
singleColorUrl = os.getenv("SINGLE_COLOR")
allMusclesUrl = os.getenv("ALL_MUSCLES")

router = APIRouter(prefix="/muscles", tags=["muscles"])


@router.get(
    "/multImg",
    summary="Generate multi-color muscle image",
    description="Generates a PNG image highlighting primary and secondary muscle groups in different colors.",
    responses={
        200: {"description": "PNG image with muscle highlights"},
        400: {"description": "Bad request or invalid parameters"},
        500: {"description": "Image generation service failed"}
    }
)
def generate_multiple_muscle_image(primary_muscles: str, secondary_muscles: str = ""):
    querystring = {
        "primaryColor": "240,100,80",
        "secondaryColor": "200,100,80",
        "primaryMuscleGroups": primary_muscles,
        "secondaryMuscleGroups": secondary_muscles,
        "transparentBackground": "0"
    }
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    response = requests.get(multiColorUrl, headers=headers, params=querystring)

    print("Status Code:", response.status_code)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch muscle image")

    return StreamingResponse(BytesIO(response.content), media_type="image/png")


@router.get(
    "/img",
    summary="Generate single-color muscle image",
    description="Generates a PNG image highlighting the specified muscle groups in one color.",
    responses={
        200: {"description": "PNG image with highlighted muscles"},
        400: {"description": "Invalid muscle group name"},
        500: {"description": "Image service failed"}
    }
)
def generate_muscle_image(muscle_groups: str):
    querystring = {
        "muscleGroups": muscle_groups,
        "color": "200,100,80",
        "transparentBackground": "0"
    }
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }
    response = requests.get(singleColorUrl, headers=headers, params=querystring)
    print("Status Code:", response.status_code)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch muscle image")

    return StreamingResponse(BytesIO(response.content), media_type="image/png")


@router.get(
    "/all",
    summary="Get list of all available muscle groups",
    description="Returns all recognized muscle group names that can be used for image generation.",
    responses={
        200: {"description": "List of all muscle groups"},
        500: {"description": "Failed to fetch muscle groups"}
    }
)
def all_muscles():
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }
    response = requests.get(allMusclesUrl, headers=headers)

    return response.json()


@router.post(
    "/upload/",
    summary="Upload muscle image and associate it with muscle name",
    description="Uploads an image to object storage and links it to the muscle name. Creates a new muscle entry if it doesn't exist.",
    responses={
        200: {
            "description": "Image uploaded successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Chest",
                        "image_url": "https://your-bucket.example.com/chest_1717251685.jpg"
                    }
                }
            }
        },
        400: {"description": "File upload failed"},
        500: {"description": "Server error"}
    }
)
def upload_muscle_image(
        name: str,
        file: UploadFile = File(...),
        db: Session = Depends(get_db)):
    file_bytes = file.file.read()

    filename = f"{name}_{int(time.time())}.jpg"

    image_url = upload_image_to_minio(file_bytes, filename, settings.MUSCLE_BUCKET)

    muscle = db.query(Muscle).filter(Muscle.name == name).first()
    if not muscle:
        muscle = Muscle(name=name)
        db.add(muscle)

    muscle.image_url = image_url
    db.commit()
    db.refresh(muscle)

    return {
        "id": muscle.id,
        "name": muscle.name,
        "image_url": muscle.image_url
    }
