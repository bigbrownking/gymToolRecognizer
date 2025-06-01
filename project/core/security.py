import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from project.core.config import settings
from project.core.database import get_db
from project.model.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
VERIFICATION_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    hashed = pwd_context.hash(password)
    logger.info("Password hashed successfully.")
    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    is_valid = pwd_context.verify(plain_password, hashed_password)
    if is_valid:
        logger.info("Password verification successful.")
    else:
        logger.warning("Password verification failed.")
    return is_valid


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})

    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Access token created for user: {data.get('sub')} with expiration: {expire}")

    return token


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info("Access token decoded successfully.")
        return payload
    except JWTError as e:
        logger.error(f"Failed to decode access token: {str(e)}")
        return None


def get_current_user(token: str = Depends(bearer_scheme), db: Session = Depends(get_db)):
    logger.info("Verifying authentication token...")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token.credentials)
    if not payload:
        logger.warning("Invalid or expired token.")
        raise credentials_exception

    email: str = payload.get("sub")
    if email is None:
        logger.warning("Token does not contain a valid email.")
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        logger.warning(f"User not found for email: {email}")
        raise credentials_exception

    logger.info(f"User authenticated successfully: {user.email}")
    return user


def generate_verification_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "sub": email,
        "exp": expire,
        "type": "email_verification"
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Verification token generated for email: {email}")
    return encoded_jwt


def verify_verification_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")

        if email is None or token_type != "email_verification":
            logger.warning("Invalid verification token - missing email or wrong type")
            return None

        logger.info(f"Verification token validated for email: {email}")
        return email
    except JWTError as e:
        logger.error(f"Failed to verify verification token: {str(e)}")
        return None


def generate_reset_token(email: str) -> str:
    """Generate password reset token"""
    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode = {
        "sub": email,
        "exp": expire,
        "type": "password_reset"
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Reset token generated for email: {email}")
    return encoded_jwt


def verify_reset_token(token: str) -> Optional[str]:
    """Verify password reset token and return the email"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")

        if email is None or token_type != "password_reset":
            logger.warning("Invalid reset token - missing email or wrong type")
            return None

        logger.info(f"Reset token validated for email: {email}")
        return email
    except JWTError as e:
        logger.error(f"Failed to verify reset token: {str(e)}")
        return None
