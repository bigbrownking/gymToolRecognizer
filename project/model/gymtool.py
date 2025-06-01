from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from project.core.database import Base


class GymTool(Base):
    __tablename__ = "gymtools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    alternative = Column(String, nullable=True)

    muscle_associations = relationship(
        "GymToolMuscleAssociation",
        back_populates="gym_tool",
        cascade="all, delete-orphan"
    )
    links = relationship("GymToolLink", back_populates="gym_tool", cascade="all, delete-orphan")

