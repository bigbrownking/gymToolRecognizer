from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from project.core.database import Base


class GymToolLink(Base):
    __tablename__ = "gymtool_links"

    id = Column(Integer, primary_key=True, index=True)
    gym_tool_id = Column(Integer, ForeignKey("gymtools.id", ondelete="CASCADE"))
    url = Column(String, nullable=False)

    gym_tool = relationship("GymTool", back_populates="links")
