from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from project.core.database import Base


class ChatFavorite(Base):
    __tablename__ = "chat_favorites"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    history_id = Column(Integer, ForeignKey("chat_histories.id"))

    user = relationship("User", back_populates="chat_favorites")
    history = relationship("ChatHistory", back_populates="favorites")