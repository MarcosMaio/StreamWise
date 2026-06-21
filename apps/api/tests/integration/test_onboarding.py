import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embedding import UserStreamingAffinity
from app.models.interaction import Interaction, UserPreference
from app.models.provider import StreamingProvider
from app.models.title import Genre, Title


async def _register_user(client: AsyncClient) -> tuple[str, str]:
    email = f"onboard-{uuid.uuid4()}@example.com"
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Onboard User"},
    )
    assert response.status_code == 201
    data = response.json()
    return data["access_token"], email


async def _seed_genre_and_provider(db_session: AsyncSession) -> tuple[Genre, StreamingProvider]:
    genre = Genre(name=f"Test Genre {uuid.uuid4().hex[:8]}", tmdb_genre_id=900000 + uuid.uuid4().int % 1000)
    provider = StreamingProvider(
        tmdb_provider_id=800000 + uuid.uuid4().int % 1000,
        name=f"Test Provider {uuid.uuid4().hex[:8]}",
        logo_path="/logo.png",
    )
    db_session.add(genre)
    db_session.add(provider)
    await db_session.flush()
    return genre, provider


async def _seed_title(db_session: AsyncSession) -> Title:
    title = Title(
        tmdb_id=700000 + uuid.uuid4().int % 1000,
        type="movie",
        title="Onboarding Seed Movie",
        overview="A title for onboarding seed likes.",
        tmdb_popularity=10.0,
        is_trending=True,
        last_synced_at=datetime.utcnow(),
    )
    db_session.add(title)
    await db_session.flush()
    return title


@pytest.mark.asyncio
async def test_preferences_requires_auth(client: AsyncClient):
    response = await client.put(
        "/users/me/preferences",
        json={"genre_ids": [], "streaming_provider_ids": []},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_preferences_validation_requires_selections(client: AsyncClient):
    token, _ = await _register_user(client)

    response = await client.put(
        "/users/me/preferences",
        json={"genre_ids": [], "streaming_provider_ids": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_save_preferences_completes_onboarding(
    client: AsyncClient,
    db_session: AsyncSession,
):
    genre, provider = await _seed_genre_and_provider(db_session)
    seed_title = await _seed_title(db_session)
    token, _ = await _register_user(client)

    me_before = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_before.status_code == 200
    assert me_before.json()["onboarding_complete"] is False

    response = await client.put(
        "/users/me/preferences",
        json={
            "genre_ids": [str(genre.id)],
            "streaming_provider_ids": [str(provider.id)],
            "seed_like_title_ids": [str(seed_title.id)],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    profile = response.json()
    assert profile["onboarding_complete"] is True
    assert profile["genre_ids"] == [str(genre.id)]
    assert profile["streaming_provider_ids"] == [str(provider.id)]

    prefs = (
        await db_session.execute(
            select(UserPreference).where(UserPreference.genre_id == genre.id)
        )
    ).scalars().all()
    assert len(prefs) == 1
    assert prefs[0].source == "onboarding"

    affinities = (
        await db_session.execute(
            select(UserStreamingAffinity).where(UserStreamingAffinity.provider_id == provider.id)
        )
    ).scalars().all()
    assert len(affinities) == 1
    assert affinities[0].score == pytest.approx(1.0)

    likes = (
        await db_session.execute(
            select(Interaction).where(
                Interaction.title_id == seed_title.id,
                Interaction.event_type == "like",
            )
        )
    ).scalars().all()
    assert len(likes) == 1


@pytest.mark.asyncio
async def test_list_genres_and_providers(
    client: AsyncClient,
    db_session: AsyncSession,
):
    genre, provider = await _seed_genre_and_provider(db_session)
    token, _ = await _register_user(client)

    genres_response = await client.get(
        "/catalog/genres",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert genres_response.status_code == 200
    genre_names = [item["name"] for item in genres_response.json()["items"]]
    assert genre.name in genre_names

    providers_response = await client.get(
        "/catalog/providers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert providers_response.status_code == 200
    provider_names = [item["name"] for item in providers_response.json()["items"]]
    assert provider.name in provider_names
