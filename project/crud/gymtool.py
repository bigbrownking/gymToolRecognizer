import logging
from sqlalchemy.orm import Session

from project.crud.muscle import get_muscle_by_name
from project.model.association import GymToolMuscleAssociation
from project.model.gymtool import GymTool
from project.model.gymtoolLink import GymToolLink
from project.schemas.gymtool import AddMuscleRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_gymtool_by_name(db: Session, name: str) -> GymTool:
    logger.info(f"Searching for gym tool: {name}")
    tool = db.query(GymTool).filter(GymTool.name == name).first()

    if tool:
        logger.info(f"Found gym tool: {name}")
        logger.info(f"Associated muscles: {[assoc.muscle.name for assoc in tool.muscle_associations]}")
        logger.info(f"Associated links: {[link.url for link in tool.links]}")
    else:
        logger.warning(f"Gym tool not found: {name}")

    return tool


def get_all_gymtools(db: Session) -> list:
    logger.info("Retrieving all gym tools with associated muscles")
    tools = db.query(GymTool).all()

    for tool in tools:
        muscles = tool.muscle_associations
        links = tool.links
        logger.info(f"Gym Tool: {tool.name}, Muscles: {[assoc.muscle.name for assoc in muscles]}, Links: {[link.url for link in links]}")

    logger.info(f"Retrieved {len(tools)} gym tools")
    return tools


def add_muscle_to_gymtool(db: Session, data: AddMuscleRequest):
    logger.info(f"Adding muscle {data.muscle_name} to gym tool {data.gymtool_name}")

    gym_tool = get_gymtool_by_name(db, data.gymtool_name)
    muscle = get_muscle_by_name(db, data.muscle_name)

    if not gym_tool or not muscle:
        logger.warning("Gym tool or muscle not found.")
        return None

    for assoc in gym_tool.muscle_associations:
        if assoc.muscle_id == muscle.id:
            logger.warning("Association already exists.")
            return None

    association = GymToolMuscleAssociation(
        gym_tool=gym_tool,
        muscle=muscle,
        primary_muscles=data.primary_muscles,
        secondary_muscles=data.secondary_muscles
    )

    db.add(association)
    db.commit()
    db.refresh(gym_tool)
    logger.info(f"Linked {muscle.name} to {gym_tool.name} with primary='{data.primary_muscles}'")
    return gym_tool


def add_link_to_gymtool(db: Session, gymtool_name: str, url: str):
    logger.info(f"Adding link to gym tool {gymtool_name}: {url}")

    gym_tool = get_gymtool_by_name(db, gymtool_name)
    if not gym_tool:
        logger.warning(f"Gym tool '{gymtool_name}' not found.")
        return None

    new_link = GymToolLink(gym_tool_id=gym_tool.id, url=url)
    db.add(new_link)
    db.commit()
    db.refresh(new_link)
    logger.info(f"Added link '{url}' to gym tool '{gymtool_name}'")
    return new_link
