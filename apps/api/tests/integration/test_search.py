import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider import StreamingProvider, TitleStreamingProvider
from app.models.title import Title


async def _register_and_token(client: AsyncClient) -> str:
    email = f"search-{uuid.uuid4()}@example.com"
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Search User"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_search_requires_auth(client: AsyncClient):
    response = await client.get("/catalog/search", params={"q": "funny"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_requires_query(client: AsyncClient):
    token = await _register_and_token(client)
    response = await client.get(
        "/catalog/search",
        params={"q": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_keyword_fallback_finds_matching_title(
    client: AsyncClient,
    db_session: AsyncSession,
):
    title = Title(
        tmdb_id=950001 + uuid.uuid4().int % 1000,
        type="series",
        title="Short Funny Series",
        overview="A quick comedy series with witty humor.",
        tmdb_popularity=55.0,
        is_trending=True,
        last_synced_at=datetime.utcnow(),
    )
    unrelated = Title(
        tmdb_id=950002 + uuid.uuid4().int % 1000,
        type="movie",
        title="Grim Drama",
        overview="A dark historical tragedy.",
        tmdb_popularity=40.0,
        is_trending=True,
        last_synced_at=datetime.utcnow(),
    )
    db_session.add_all([title, unrelated])
    await db_session.flush()

    token = await _register_and_token(client)
    response = await client.get(
        "/catalog/search",
        params={"q": "funny series"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert "Short Funny Series" in titles
    assert "Grim Drama" not in titles


@pytest.mark.asyncio
async def test_search_filters_by_provider(
    client: AsyncClient,
    db_session: AsyncSession,
):
    netflix = StreamingProvider(tmdb_provider_id=980001, name="Netflix", logo_path="/n.png")
    prime = StreamingProvider(tmdb_provider_id=980002, name="Prime", logo_path="/p.png")
    db_session.add_all([netflix, prime])
    await db_session.flush()

    netflix_title = Title(
        tmdb_id=960001 + uuid.uuid4().int % 1000,
        type="movie",
        title="Netflix Comedy Special",
        overview="Funny stand-up on Netflix.",
        tmdb_popularity=60.0,
        last_synced_at=datetime.utcnow(),
    )
    prime_title = Title(
        tmdb_id=960002 + uuid.uuid4().int % 1000,
        type="movie",
        title="Prime Comedy Special",
        overview="Funny stand-up on Prime.",
        tmdb_popularity=59.0,
        last_synced_at=datetime.utcnow(),
    )
    db_session.add_all([netflix_title, prime_title])
    await db_session.flush()
    db_session.add_all(
        [
            TitleStreamingProvider(
                title_id=netflix_title.id,
                provider_id=netflix.id,
                country_code="BR",
                availability_type="flatrate",
            ),
            TitleStreamingProvider(
                title_id=prime_title.id,
                provider_id=prime.id,
                country_code="BR",
                availability_type="flatrate",
            ),
        ]
    )
    await db_session.flush()

    token = await _register_and_token(client)
    response = await client.get(
        "/catalog/search",
        params={"q": "comedy", "provider_ids": [str(netflix.id)]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert "Netflix Comedy Special" in titles
    assert "Prime Comedy Special" not in titles
