import logging
from datetime import date

from sqlalchemy.orm import Session

from project.core.security import hash_password, verify_password
from project.model.user import User
from project.schemas.user import UserCreate, UserProfileUpdate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_age(date_of_birth: date) -> int:
    today = date.today()
    age = today.year - date_of_birth.year

    if today.month < date_of_birth.month or (today.month == date_of_birth.month and today.day < date_of_birth.day):
        age -= 1

    return age


def create_user(db: Session, user_data: UserCreate, is_active: bool = False):
    hashed_pw = hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        password=hashed_pw,
        gender=user_data.gender,
        username=user_data.username,
        dateOfBirth=user_data.dateOfBirth,
        is_active=is_active,
        is_sub=False,
        free_attempts=5
    )

    logger.info(f"User is : {new_user}")
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info(f"User created: {new_user.email}")
    return new_user


def create_oauth_user(
        db: Session,
        email: str,
        username: str,
        oauth_provider: str,
        oauth_id: str
) -> User:
    db_user = User(
        email=email,
        username=username,
        password=None,
        is_oauth_user=True,
        oauth_provider=oauth_provider,
        oauth_id=oauth_id,
        is_active=True,
        is_sub=False,
        free_attempts=5,
        gender=None,
        dateOfBirth=None,
        age=None
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()

    if not user:
        logger.warning(f"Authentication failed - user not found: {email}")
        return None

    if user.is_oauth_user:
        logger.warning(f"Authentication failed - OAuth user trying password login: {email}")
        return None

    if user.password and verify_password(password, user.password):
        logger.info(f"User authenticated: {email}")
        return user

    logger.warning(f"Authentication failed for: {email}")
    return None


def get_profile(db: Session, email: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.warning(f"Profile not found for email: {email}")
        return None

    if user.dateOfBirth:
        current_age = calculate_age(user.dateOfBirth)
        if user.age != current_age:
            user.age = current_age
            db.commit()
            db.refresh(user)
            logger.info(f"Age updated for user {email}: {current_age}")

    logger.info(f"Profile retrieved for email: {email}")
    return user


def update_profile(db: Session, email: str, profile_data: UserProfileUpdate):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.warning(f"Update failed - User not found: {email}")
        return None

    if profile_data.username is not None:
        user.username = profile_data.username

    if hasattr(profile_data, 'gender') and profile_data.gender is not None:
        user.gender = profile_data.gender

    if hasattr(profile_data, 'dateOfBirth') and profile_data.dateOfBirth is not None:
        user.dateOfBirth = profile_data.dateOfBirth
        user.age = calculate_age(profile_data.dateOfBirth)

    if user.dateOfBirth:
        current_age = calculate_age(user.dateOfBirth)
        if user.age != current_age:
            user.age = current_age
            logger.info(f"Age updated for user {email}: {current_age}")

    db.commit()
    db.refresh(user)

    logger.info(f"Profile updated for email: {email}")
    return user


def update_profile_image(db: Session, email: str, image_url: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.warning(f"Update profile image failed - User not found: {email}")
        return None

    user.profile_image_url = image_url

    if user.dateOfBirth:
        current_age = calculate_age(user.dateOfBirth)
        if user.age != current_age:
            user.age = current_age
            logger.info(f"Age updated for user {email}: {current_age}")

    db.commit()
    db.refresh(user)

    logger.info(f"Profile image updated for email: {email}")
    return user


def delete_user(db: Session, email: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.warning(f"Delete failed - User not found: {email}")
        return None

    db.delete(user)
    db.commit()
    logger.info(f"User deleted: {email}")
    return {"message": "User deleted successfully"}


def activate_user(db: Session, user_id: int = None, email: str = None):
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
    elif email:
        user = db.query(User).filter(User.email == email).first()
    else:
        logger.warning("Activate failed - No user ID or email provided")
        return None

    if not user:
        logger.warning(f"Activate failed - User not found: {user_id or email}")
        return None

    user.is_active = True
    db.commit()
    db.refresh(user)
    logger.info(f"User activated: {user.email}")
    return user
