from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
import logging

from core.database import get_db
from crud.gymtool import get_all_gymtools, get_gymtool_by_name, add_muscle_to_gymtool, add_link_to_gymtool
from schemas.gymtool import AddMuscleRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tool", tags=["gymtools"])


@router.get(
    "/all",
    summary="Get all gym tools",
    description="Returns a list of all gym tools available in the database.",
    responses={
        200: {
            "description": "List of gym tools",
            "content": {
                "application/json": {
                    "example": [
                        {"name": "Barbell", "muscles": ["Chest", "Biceps"], "links": ["https://example.com"]},
                        {"name": "Dumbbell", "muscles": ["Shoulders"], "links": []}
                    ]
                }
            }
        }
    }
)
def read_all_tools(db: Session = Depends(get_db)):
    return get_all_gymtools(db)


@router.get(
    "/profile",
    summary="Get details of a specific gym tool",
    description="Returns the detailed profile of a gym tool by its name.",
    responses={
        200: {
            "description": "Gym tool found",
            "content": {
                "application/json": {
                    "example": {
                        "name": "Barbell",
                        "muscles": ["Chest", "Biceps"],
                        "links": ["https://example.com/tutorial"]
                    }
                }
            }
        },
        404: {"description": "Gym tool not found"}
    }
)
def read_tool(name: str, db: Session = Depends(get_db)):
    tool = get_gymtool_by_name(db, name)
    if not tool:
        raise HTTPException(status_code=404, detail="Gym tool not found")
    return tool


@router.post(
    "/add-muscle",
    summary="Add muscle to gym tool",
    description="Associates a muscle group with a gym tool. Useful for categorization and recommendations.",
    responses={
        200: {
            "description": "Muscle added successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Muscle 'Chest' added successfully to 'Barbell'"
                    }
                }
            }
        },
        400: {"description": "Invalid request or tool not found"}
    }
)
def add_muscle(
    data: AddMuscleRequest,
    db: Session = Depends(get_db)
):
    gym_tool = add_muscle_to_gymtool(db, data)
    if not gym_tool:
        raise HTTPException(status_code=400, detail="Failed to add muscle to gym tool")
    return {"message": f"Muscle '{data.muscle_name}' added successfully to '{data.gymtool_name}'"}


@router.post(
    "/add-link",
    summary="Add link to gym tool",
    description="Adds a relevant external link (e.g. video or tutorial) to a specific gym tool.",
    responses={
        200: {
            "description": "Link added successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Link 'https://example.com' added successfully to 'Barbell'"
                    }
                }
            }
        },
        400: {"description": "Invalid tool or failed to add link"}
    }
)
def add_link(
    gymtool_name: str = Query(..., title="Gym Tool Name"),
    url: str = Query(..., title="Link URL"),
    db: Session = Depends(get_db)
):
    new_link = add_link_to_gymtool(db, gymtool_name, url)
    if not new_link:
        raise HTTPException(status_code=400, detail="Failed to add link to gym tool")
    return {"message": f"Link '{url}' added successfully to '{gymtool_name}'"}