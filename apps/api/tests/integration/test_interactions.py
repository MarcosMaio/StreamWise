import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embedding import UserStreamingAffinity
from app.models.interaction import Interaction
from app.models.provider import StreamingProvider, TitleStreamingProvider
from app.models.title import Title


async def _register_and_token(client: AsyncClient) -> str:
    email = f"interaction-{uuid.uuid4()}@example.com"
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Interaction User"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


async def _seed_title_with_provider(db_session: AsyncSession) -> tuple[Title, StreamingProvider]:
    provider = StreamingProvider(
        tmdb_provider_id=820000 + uuid.uuid4().int % 1000,
        name="Prime Video",
        logo_path="/prime.jpg",
    )
    title = Title(
        tmdb_id=620000 + uuid.uuid4().int % 1000,
        type="movie",
        title="Interaction Test Movie",
        overview="Used for interaction integration tests.",
        tmdb_popularity=42.0,
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
async def test_interaction_requires_auth(client: AsyncClient):
    title_id = uuid.uuid4()
    response = await client.post(
        f"/titles/{title_id}/interactions",
        json={"event_type": "like"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_like_and_rate_update_aggregates(
    client: AsyncClient,
    db_session: AsyncSession,
):
    title, _provider = await _seed_title_with_provider(db_session)
    token = await _register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    like_response = await client.post(
        f"/titles/{title.id}/interactions",
        json={"event_type": "like"},
        headers=headers,
    )
    assert like_response.status_code == 201
    like_data = like_response.json()
    assert like_data["event_type"] == "like"
    assert like_data["title"]["like_count"] == 1

    rating_response = await client.post(
        f"/titles/{title.id}/interactions",
        json={"event_type": "rating", "rating": 5},
        headers=headers,
    )
    assert rating_response.status_code == 201
    rating_data = rating_response.json()
    assert rating_data["title"]["streamwise_avg_rating"] == pytest.approx(5.0)

    refreshed = await client.get(f"/titles/{title.id}", headers=headers)
    assert refreshed.status_code == 200
    refreshed_data = refreshed.json()
    assert refreshed_data["like_count"] == 1
    assert refreshed_data["streamwise_avg_rating"] == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_like_and_dislike_are_mutually_exclusive(
    client: AsyncClient,
    db_session: AsyncSession,
):
    title, _provider = await _seed_title_with_provider(db_session)
    token = await _register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        f"/titles/{title.id}/interactions",
        json={"event_type": "like"},
        headers=headers,
    )

    dislike_response = await client.post(
        f"/titles/{title.id}/interactions",
        json={"event_type": "dislike"},
        headers=headers,
    )
    assert dislike_response.status_code == 201
    assert dislike_response.json()["title"]["like_count"] == 0

    likes = (
        await db_session.execute(
            select(Interaction).where(
                Interaction.title_id == title.id,
                Interaction.event_type == "like",
            )
        )
    ).scalars().all()
    dislikes = (
        await db_session.execute(
            select(Interaction).where(
                Interaction.title_id == title.id,
                Interaction.event_type == "dislike",
            )
        )
    ).scalars().all()
    assert len(likes) == 0
    assert len(dislikes) == 1


@pytest.mark.asyncio
async def test_like_recomputes_streaming_affinity(
    client: AsyncClient,
    db_session: AsyncSession,
):
    title, provider = await _seed_title_with_provider(db_session)
    token = await _register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        f"/titles/{title.id}/interactions",
        json={"event_type": "like"},
        headers=headers,
    )
    assert response.status_code == 201

    affinities = (
        await db_session.execute(
            select(UserStreamingAffinity).where(UserStreamingAffinity.provider_id == provider.id)
        )
    ).scalars().all()
    assert len(affinities) == 1
    assert affinities[0].score == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_rating_requires_value(client: AsyncClient, db_session: AsyncSession):
    title, _provider = await _seed_title_with_provider(db_session)
    token = await _register_and_token(client)

    response = await client.post(
        f"/titles/{title.id}/interactions",
        json={"event_type": "rating"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
