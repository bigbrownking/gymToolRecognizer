from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from project.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, index=True)
    age = Column(Integer, nullable=True)
    password = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    is_active = Column(Boolean, default=False)
    is_sub = Column(Boolean, default=False)
    free_attempts = Column(Integer)
    sub_until = Column(DateTime, nullable=True)
    dateOfBirth = Column(Date, nullable=True)
    profile_image_url = Column(String, nullable=True)

    is_oauth_user = Column(Boolean, default=False)
    oauth_provider = Column(String, nullable=True)
    oauth_id = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    gym_logs = relationship("UserGymLog", back_populates="user", cascade="all, delete-orphan")
    chat_histories = relationship("ChatHistory", back_populates="user")
    chat_favorites = relationship("ChatFavorite", back_populates="user")
    payments = relationship("Payment", back_populates="user")
