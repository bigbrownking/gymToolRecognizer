from dotenv import load_dotenv
from pydantic_settings import BaseSettings
import os

load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Recognizing GYM Tools")
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 480))

    MINIO_URL: str = os.getenv("MINIO_URL")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY")
    MUSCLE_BUCKET: str = os.getenv("MUSCLE_BUCKET")
    PROFILE_BUCKET: str = os.getenv("PROFILE_IMAGE_BUCKET")

    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLEKEY: str = os.getenv("STRIPE_PUBLISHABLEKEY")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET")

    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN")
    GITHUB_MODEL_ENDPOINT: str = os.getenv("GITHUB_MODEL_ENDPOINT")
    MODEL: str = os.getenv("MODEL")

    TOGIS_TOKEN: str = os.getenv("TOGIS_TOKEN")
    TOGIS_URL: str = os.getenv("TOGIS_URL")

    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI")

    MICROSOFT_CLIENT_ID: str = os.getenv("MICROSOFT_CLIENT_ID")
    MICROSOFT_CLIENT_SECRET: str = os.getenv("MICROSOFT_CLIENT_SECRET")
    MICROSOFT_REDIRECT_URI: str = os.getenv("MICROSOFT_REDIRECT_URI")

    DISCORD_CLIENT_ID: str = os.getenv("DISCORD_CLIENT_ID")
    DISCORD_CLIENT_SECRET: str = os.getenv("DISCORD_CLIENT_SECRET")
    DISCORD_REDIRECT_URI: str = os.getenv("DISCORD_REDIRECT_URI")

    SMTP_SERVER: str = os.getenv("SMTP_SERVER")
    SMTP_PORT: str = os.getenv("SMTP_PORT")
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL")
    FROM_NAME: str = os.getenv("FROM_NAME")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


settings = Settings()

