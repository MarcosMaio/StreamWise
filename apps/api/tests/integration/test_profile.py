import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider import StreamingProvider, TitleStreamingProvider
from app.models.title import Title


async def _register_and_token(client: AsyncClient) -> str:
    email = f"profile-{uuid.uuid4()}@example.com"
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Profile User"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


async def _seed_title_with_provider(
    db_session: AsyncSession,
    *,
    title_name: str,
) -> tuple[Title, StreamingProvider]:
    provider = StreamingProvider(
        tmdb_provider_id=990000 + uuid.uuid4().int % 1000,
        name="Netflix",
        logo_path="/netflix.png",
    )
    title = Title(
        tmdb_id=990000 + uuid.uuid4().int % 1000,
        type="movie",
        title=title_name,
        overview="Profile integration test title.",
        tmdb_popularity=50.0,
        last_synced_at=datetime.utcnow(),
    )
    db_session.add(provider)
    db_session.add(title)
    await db_session.flush()
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
async def test_profile_endpoints_require_auth(client: AsyncClient):
    for path in ("/users/me/likes", "/users/me/watchlist", "/users/me/affinity"):
        response = await client.get(path)
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_likes_lists_liked_titles(client: AsyncClient, db_session: AsyncSession):
    liked_title, _provider = await _seed_title_with_provider(
        db_session,
        title_name="Profile Liked Movie",
    )
    other_title, _ = await _seed_title_with_provider(
        db_session,
        title_name="Profile Other Movie",
    )
    token = await _register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    like_response = await client.post(
        f"/titles/{liked_title.id}/interactions",
        json={"event_type": "like"},
        headers=headers,
    )
    assert like_response.status_code == 201

    response = await client.get("/users/me/likes", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    titles = [item["title"] for item in payload["items"]]
    assert "Profile Liked Movie" in titles
    assert "Profile Other Movie" not in titles
    assert payload["total"] == 1


@pytest.mark.asyncio
async def test_watchlist_lists_saved_titles(client: AsyncClient, db_session: AsyncSession):
    watchlist_title, _provider = await _seed_title_with_provider(
        db_session,
        title_name="Profile Watchlist Movie",
    )
    token = await _register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    watchlist_response = await client.post(
        f"/titles/{watchlist_title.id}/interactions",
        json={"event_type": "watchlist"},
        headers=headers,
    )
    assert watchlist_response.status_code == 201

    response = await client.get("/users/me/watchlist", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    titles = [item["title"] for item in payload["items"]]
    assert "Profile Watchlist Movie" in titles
    assert payload["total"] == 1


@pytest.mark.asyncio
async def test_affinity_returns_dominant_provider_after_likes(
    client: AsyncClient,
    db_session: AsyncSession,
):
    title, provider = await _seed_title_with_provider(
        db_session,
        title_name="Affinity Test Movie",
    )
    token = await _register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    like_response = await client.post(
        f"/titles/{title.id}/interactions",
        json={"event_type": "like"},
        headers=headers,
    )
    assert like_response.status_code == 201

    response = await client.get("/users/me/affinity", headers=headers)
    assert response.status_code == 200
    providers = response.json()["providers"]
    assert len(providers) == 1
    assert providers[0]["provider_id"] == str(provider.id)
    assert providers[0]["provider_name"] == "Netflix"
    assert providers[0]["score"] == pytest.approx(1.0)
