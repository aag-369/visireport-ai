import asyncio
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_visireport.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("MODEL_WEIGHTS_PATH", "/nonexistent/best.pt")
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:59999/")  # deliberately unreachable

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.db import Base, engine, AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User


@pytest_asyncio.fixture(scope="function", autouse=True)
async def _fresh_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        db.add(
            User(
                email="engineer@visireport.ai",
                name="QA Engineer",
                role="engineer",
                hashed_password=hash_password("test-password"),
            )
        )
        await db.commit()
    yield


@pytest_asyncio.fixture
async def client():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "engineer@visireport.ai", "password": "test-password"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
