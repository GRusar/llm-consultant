import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.db.base import Base
from app.api.deps import get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def client():
    engine = create_async_engine(TEST_DB_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def test_register_success(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "user@example.com"
    assert data["role"] == "user"
    assert "id" in data
    assert "password_hash" not in data


async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "duplicate@example.com", "password": "password123"}
    await client.post("/auth/register", json=payload)
    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 409


async def test_login_success(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={"email": "loginuser@example.com", "password": "password123"},
    )
    response = await client.post(
        "/auth/login",
        data={"username": "loginuser@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={"email": "wrongpass@example.com", "password": "password123"},
    )
    response = await client.post(
        "/auth/login",
        data={"username": "wrongpass@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


async def test_me_success(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={"email": "meuser@example.com", "password": "password123"},
    )
    login = await client.post(
        "/auth/login",
        data={"username": "meuser@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]

    response = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "meuser@example.com"


async def test_me_no_token(client: AsyncClient):
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_me_invalid_token(client: AsyncClient):
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer this.is.garbage"},
    )
    assert response.status_code == 401
