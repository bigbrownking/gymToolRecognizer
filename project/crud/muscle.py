import logging

from sqlalchemy.orm import Session

from project.model.muscle import Muscle


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_muscle_by_name(db: Session, name: str) -> Muscle:
    logger.info(f"Searching for muscle: {name}")
    muscle = db.query(Muscle).filter(Muscle.name == name).first()

    if muscle:
        logger.info(f"Found muscle: {name}")
    else:
        logger.warning(f"Muscle not found: {name}")

    return muscle
