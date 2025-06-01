import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from project.core.database import get_db
from project.core.security import get_current_user
from project.crud.user_gym_logs import set_gym_flag, get_user_gym_logs, get_user_gym_log_by_date
from project.model.user import User
from project.schemas.user_gym_log import GymLogRequest

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/gym-log", tags=["gym-log"])


@router.patch(
    "/flag",
    summary="Mark gym attendance",
    description="Mark a specific date as gym attended or missed by the user.",
    responses={
        200: {"description": "Attendance marked successfully"},
        400: {"description": "Invalid data"},
        500: {"description": "Internal server error"}
    }
)
def mark_attendance(
    data: GymLogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"[Attendance] User {current_user.email} is marking {data.date} as {'attended' if data.went else 'missed'}")
    try:
        result = set_gym_flag(db, current_user.id, data)
        logger.info(f"[Attendance] Update successful for {current_user.email} on {data.date}")
        return result
    except Exception as e:
        logger.error(f"[Attendance] Failed to mark attendance for {current_user.email} - Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark attendance")


@router.get(
    "/logs",
    summary="Get all gym logs",
    description="Retrieve all gym attendance logs for the current user.",
    responses={
        200: {"description": "Logs retrieved successfully"},
        500: {"description": "Internal server error"}
    }
)
def get_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"[Logs] Retrieving gym logs for user: {current_user.email}")
    try:
        logs = get_user_gym_logs(db, current_user.id)
        logger.info(f"[Logs] Retrieved {len(logs)} log entries for {current_user.email}")
        return logs
    except Exception as e:
        logger.error(f"[Logs] Failed to retrieve logs for {current_user.email} - Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")


@router.get(
    "/{log_date}",
    summary="Get gym log by date",
    description="Retrieve a specific gym log for the user by date.",
    responses={
        200: {"description": "Log entry found"},
        404: {"description": "Log entry not found"},
        500: {"description": "Internal server error"}
    }
)
def get_log_by_date(
    log_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"[Logs] Retrieving gym log for user: {current_user.email} on date: {log_date}")
    try:
        log_entry = get_user_gym_log_by_date(db, current_user.id, log_date)
        if not log_entry:
            raise HTTPException(status_code=404, detail="Log entry not found")
        logger.info(f"[Logs] Retrieved log for {current_user.email} on {log_date}")
        return log_entry
    except Exception as e:
        logger.error(f"[Logs] Failed to retrieve log for {current_user.email} on {log_date} - Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve log entry")
