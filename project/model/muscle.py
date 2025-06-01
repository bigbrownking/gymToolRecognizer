from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from project.core.database import Base


class Muscle(Base):
    __tablename__ = "muscles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    image_url = Column(String, nullable=True)

    tool_associations = relationship(
        "GymToolMuscleAssociation",
        back_populates="muscle",
        cascade="all, delete-orphan"
    )
