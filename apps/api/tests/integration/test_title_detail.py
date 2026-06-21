import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider import StreamingProvider, TitleStreamingProvider
from app.models.title import Genre, Title, TitleGenre


async def _register_and_token(client: AsyncClient) -> str:
    email = f"detail-{uuid.uuid4()}@example.com"
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Detail User"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


async def _seed_title_with_provider(db_session: AsyncSession) -> tuple[Title, StreamingProvider]:
    genre = Genre(name=f"Detail Genre {uuid.uuid4().hex[:8]}", tmdb_genre_id=910000 + uuid.uuid4().int % 1000)
    provider = StreamingProvider(
        tmdb_provider_id=810000 + uuid.uuid4().int % 1000,
        name="Netflix",
        logo_path="/t/p/original/netflix.jpg",
    )
    title = Title(
        tmdb_id=600000 + uuid.uuid4().int % 1000,
        type="movie",
        title="Detail Test Movie",
        overview="A detailed synopsis for integration testing.",
        tmdb_popularity=88.0,
        streamwise_avg_rating=4.2,
        like_count=12,
        is_trending=True,
        last_synced_at=datetime.utcnow(),
    )
    db_session.add(genre)
    db_session.add(provider)
    db_session.add(title)
    await db_session.flush()

    db_session.add(TitleGenre(title_id=title.id, genre_id=genre.id))
    db_session.add(
        TitleStreamingProvider(
            title_id=title.id,
            provider_id=provider.id,
            country_code="BR",
            availability_type="flatrate",
        )
    )
    await db_session.flush()
    return title, provider


@pytest.mark.asyncio
async def test_title_detail_requires_auth(client: AsyncClient):
    title_id = uuid.uuid4()
    response = await client.get(f"/titles/{title_id}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_title_detail_not_found(client: AsyncClient):
    token = await _register_and_token(client)
    title_id = uuid.uuid4()

    response = await client.get(
        f"/titles/{title_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_title_detail_returns_metadata_and_providers(
    client: AsyncClient,
    db_session: AsyncSession,
):
    title, provider = await _seed_title_with_provider(db_session)
    token = await _register_and_token(client)

    response = await client.get(
        f"/titles/{title.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Detail Test Movie"
    assert data["overview"] == "A detailed synopsis for integration testing."
    assert data["streamwise_avg_rating"] == pytest.approx(4.2)
    assert data["like_count"] == 12
    assert data["is_trending"] is True
    assert len(data["genres"]) == 1
    assert len(data["streaming_providers"]) == 1
    assert data["streaming_providers"][0]["name"] == provider.name
    assert data["streaming_providers"][0]["availability_type"] == "flatrate"


@pytest.mark.asyncio
async def test_title_detail_without_providers(
    client: AsyncClient,
    db_session: AsyncSession,
):
    title = Title(
        tmdb_id=600100 + uuid.uuid4().int % 1000,
        type="series",
        title="Unavailable Series",
        overview="No streaming providers linked.",
        tmdb_popularity=10.0,
        last_synced_at=datetime.utcnow(),
    )
    db_session.add(title)
    await db_session.flush()

    token = await _register_and_token(client)
    response = await client.get(
        f"/titles/{title.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["streaming_providers"] == []
