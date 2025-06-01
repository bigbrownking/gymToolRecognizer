import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from fastapi import FastAPI, Depends

from project.core.database import Base, get_db
from project.main import app
from project.model.user import User

from project.core.security import get_current_user

# Setup test database (adjust connection string as needed)
DATABASE_URL = "sqlite+aiosqlite:///./test.db"  # async SQLite for tests

# Create async engine and session for tests
engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# Override get_db dependency to use test DB session
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


# Dummy user fixture (mock current user)
@pytest.fixture
def test_user():
    return User(
        id=1,
        email="test@example.com",
        age=25,
        gender="male",
        # add other required User fields if needed
    )


# Override get_current_user dependency to use test_user fixture
def override_get_current_user():
    return test_user()


@pytest.fixture(scope="module")
async def async_client():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides = {}  # Reset overrides after tests
