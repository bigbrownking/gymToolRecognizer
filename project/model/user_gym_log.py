from sqlalchemy import Column, Integer, ForeignKey, Date, Boolean, String
from sqlalchemy.orm import relationship
from project.core.database import Base


class UserGymLog(Base):
    __tablename__ = "user_gym_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, index=True)
    went_to_gym = Column(Boolean, default=False)
    action = Column(String)

    user = relationship("User", back_populates="gym_logs")
