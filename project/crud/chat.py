from project.model.chatHistory import ChatHistory
from project.model.chatFavorites import ChatFavorite
from sqlalchemy.orm import Session


def add_workout_to_history(db: Session, user_id: int, goal: str, plan: str):
    db_history = ChatHistory(user_id=user_id, goal=goal, plan=plan)
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    return db_history


def add_to_favorites(db: Session, user_id: int, history_id: int):
    db_favorite = ChatFavorite(user_id=user_id, history_id=history_id)
    db.add(db_favorite)
    db.commit()
    db.refresh(db_favorite)
    return db_favorite


def remove_from_favorites(db: Session, user_id: int, history_id: int):
    db_favorite = db.query(ChatFavorite).filter(
        ChatFavorite.user_id == user_id,
        ChatFavorite.history_id == history_id
    ).first()
    if db_favorite:
        db.delete(db_favorite)
        db.commit()
    return db_favorite


def get_user_history(db: Session, user_id: int):
    return db.query(ChatHistory).filter(ChatHistory.user_id == user_id).all()


def get_user_favorites_as_history(db: Session, user_id: int):
    return db.query(ChatHistory).join(
        ChatFavorite, ChatHistory.id == ChatFavorite.history_id
    ).filter(ChatFavorite.user_id == user_id).all()
