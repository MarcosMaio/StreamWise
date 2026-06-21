import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embedding import TitleEmbedding
from app.models.provider import StreamingProvider
from app.models.title import Genre, Title, TitleGenre


def _unit_vector(index: int, dim: int = 384) -> list[float]:
    vector = [0.0] * dim
    vector[index % dim] = 1.0
    return vector


async def _register_and_token(client: AsyncClient) -> str:
    email = f"recs-{uuid.uuid4()}@example.com"
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Recs User"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


async def _seed_catalog(db_session: AsyncSession) -> tuple[Genre, StreamingProvider, list[Title], Title, Title]:
    genre = Genre(name=f"Recs Genre {uuid.uuid4().hex[:8]}", tmdb_genre_id=940000 + uuid.uuid4().int % 1000)
    provider = StreamingProvider(
        tmdb_provider_id=840000 + uuid.uuid4().int % 1000,
        name="Rec Provider",
        logo_path="/logo.png",
    )
    db_session.add(genre)
    db_session.add(provider)
    await db_session.flush()

    titles: list[Title] = []
    for index in range(12):
        title = Title(
            tmdb_id=730000 + uuid.uuid4().int % 1000 + index,
            type="movie",
            title=f"Rec Title {index}",
            overview=f"Overview for recommendation title {index}.",
            tmdb_popularity=90.0 - index,
            is_trending=index >= 7,
            last_synced_at=datetime.utcnow(),
        )
        db_session.add(title)
        titles.append(title)

    await db_session.flush()

    for index, title in enumerate(titles):
        db_session.add(TitleGenre(title_id=title.id, genre_id=genre.id))
        vector_index = 0 if index < 7 else 1
        db_session.add(
            TitleEmbedding(
                title_id=title.id,
                content_vector=_unit_vector(vector_index),
            )
        )

    await db_session.flush()
    watched = titles[5]
    disliked = titles[6]
    return genre, provider, titles, watched, disliked


@pytest.mark.asyncio
async def test_for_you_requires_auth(client: AsyncClient):
    response = await client.get("/recommendations/for-you")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_for_you_returns_personalized_feed_excluding_blocked_titles(
    client: AsyncClient,
    db_session: AsyncSession,
):
    genre, provider, titles, watched, disliked = await _seed_catalog(db_session)
    token = await _register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    prefs_response = await client.put(
        "/users/me/preferences",
        json={
            "genre_ids": [str(genre.id)],
            "streaming_provider_ids": [str(provider.id)],
        },
        headers=headers,
    )
    assert prefs_response.status_code == 200

    liked_titles = titles[:5]
    for title in liked_titles:
        response = await client.post(
            f"/titles/{title.id}/interactions",
            json={"event_type": "like"},
            headers=headers,
        )
        assert response.status_code == 201

    watched_response = await client.post(
        f"/titles/{watched.id}/interactions",
        json={"event_type": "watched"},
        headers=headers,
    )
    assert watched_response.status_code == 201

    dislike_response = await client.post(
        f"/titles/{disliked.id}/interactions",
        json={"event_type": "dislike"},
        headers=headers,
    )
    assert dislike_response.status_code == 201

    feed_response = await client.get(
        "/recommendations/for-you?limit=20",
        headers=headers,
    )
    assert feed_response.status_code == 200
    feed = feed_response.json()
    assert len(feed["items"]) >= 10

    result_ids = {item["id"] for item in feed["items"]}
    assert str(watched.id) not in result_ids
    assert str(disliked.id) not in result_ids


@pytest.mark.asyncio
async def test_for_you_cold_start_uses_onboarding_genres(
    client: AsyncClient,
    db_session: AsyncSession,
):
    genre, provider, titles, _, _ = await _seed_catalog(db_session)
    token = await _register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    await client.put(
        "/users/me/preferences",
        json={"genre_ids": [str(genre.id)], "streaming_provider_ids": [str(provider.id)]},
        headers=headers,
    )

    response = await client.get("/recommendations/for-you?limit=5", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
