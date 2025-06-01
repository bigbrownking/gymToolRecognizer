from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from project.core.database import Base


class GymToolMuscleAssociation(Base):
    __tablename__ = "gymtool_muscle_association"

    gymtool_id = Column(Integer, ForeignKey("gymtools.id"), primary_key=True)
    muscle_id = Column(Integer, ForeignKey("muscles.id"), primary_key=True)
    primary_muscles = Column(String, nullable=False)
    secondary_muscles = Column(String, nullable=True)

    gym_tool = relationship("GymTool", back_populates="muscle_associations")
    muscle = relationship("Muscle", back_populates="tool_associations")