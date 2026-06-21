import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.title import Title


async def _register_and_token(client: AsyncClient) -> str:
    email = f"catalog-{uuid.uuid4()}@example.com"
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Catalog User"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


async def _seed_trending_title(db_session: AsyncSession) -> Title:
    title = Title(
        tmdb_id=999001,
        type="movie",
        title="Test Trending Movie",
        overview="A test title for catalog integration.",
        tmdb_popularity=99.5,
        is_trending=True,
        is_new_release=False,
        last_synced_at=datetime.utcnow(),
    )
    db_session.add(title)
    await db_session.flush()
    return title


@pytest.mark.asyncio
async def test_trending_requires_auth(client: AsyncClient):
    response = await client.get("/catalog/trending")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_trending_returns_seeded_title(client: AsyncClient, db_session: AsyncSession):
    await _seed_trending_title(db_session)
    token = await _register_and_token(client)

    response = await client.get(
        "/catalog/trending",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(item["title"] == "Test Trending Movie" for item in data["items"])


@pytest.mark.asyncio
async def test_new_releases_returns_seeded_title(client: AsyncClient, db_session: AsyncSession):
    title = Title(
        tmdb_id=999002,
        type="series",
        title="Test New Series",
        overview="A new series for catalog integration.",
        tmdb_popularity=50.0,
        is_trending=False,
        is_new_release=True,
        last_synced_at=datetime.utcnow(),
    )
    db_session.add(title)
    await db_session.flush()

    token = await _register_and_token(client)
    response = await client.get(
        "/catalog/new",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(item["title"] == "Test New Series" for item in data["items"])
