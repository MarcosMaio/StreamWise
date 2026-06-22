import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embedding import TitleEmbedding
from app.models.title import Genre, Title, TitleGenre


def _unit_vector(index: int, dim: int = 384) -> list[float]:
    vector = [0.0] * dim
    vector[index % dim] = 1.0
    return vector


async def _register_and_token(client: AsyncClient) -> str:
    email = f"similar-{uuid.uuid4()}@example.com"
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Similar User"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


async def _seed_similar_titles(db_session: AsyncSession) -> tuple[Title, Title, Title]:
    genre = Genre(name=f"Sci-Fi {uuid.uuid4().hex[:8]}", tmdb_genre_id=930000 + uuid.uuid4().int % 1000)
    db_session.add(genre)
    await db_session.flush()

    source = Title(
        tmdb_id=710000 + uuid.uuid4().int % 1000,
        type="movie",
        title="Source Movie",
        overview="Space exploration epic.",
        last_synced_at=datetime.utcnow(),
    )
    neighbor = Title(
        tmdb_id=710001 + uuid.uuid4().int % 1000,
        type="movie",
        title="Neighbor Movie",
        overview="Another space adventure.",
        last_synced_at=datetime.utcnow(),
    )
    distant = Title(
        tmdb_id=710002 + uuid.uuid4().int % 1000,
        type="movie",
        title="Distant Movie",
        overview="Romantic comedy downtown.",
        last_synced_at=datetime.utcnow(),
    )
    db_session.add_all([source, neighbor, distant])
    await db_session.flush()

    for title in (source, neighbor, distant):
        db_session.add(TitleGenre(title_id=title.id, genre_id=genre.id))

    db_session.add_all(
        [
            TitleEmbedding(title_id=source.id, content_vector=_unit_vector(0)),
            TitleEmbedding(title_id=neighbor.id, content_vector=_unit_vector(0)),
            TitleEmbedding(title_id=distant.id, content_vector=_unit_vector(1)),
        ]
    )
    await db_session.flush()
    return source, neighbor, distant


@pytest.mark.asyncio
async def test_similar_requires_auth(client: AsyncClient):
    title_id = uuid.uuid4()
    response = await client.get(f"/titles/{title_id}/similar")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_similar_title_not_found(client: AsyncClient):
    token = await _register_and_token(client)
    title_id = uuid.uuid4()

    response = await client.get(
        f"/titles/{title_id}/similar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_similar_returns_closest_neighbors(
    client: AsyncClient,
    db_session: AsyncSession,
):
    source, neighbor, distant = await _seed_similar_titles(db_session)
    token = await _register_and_token(client)

    response = await client.get(
        f"/titles/{source.id}/similar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    result_ids = [item["id"] for item in data["items"]]
    assert result_ids[0] == str(neighbor.id)
    assert str(source.id) not in result_ids


@pytest.mark.asyncio
async def test_similar_without_embedding_returns_empty(
    client: AsyncClient,
    db_session: AsyncSession,
):
    title = Title(
        tmdb_id=720000 + uuid.uuid4().int % 1000,
        type="movie",
        title="Unembedded Movie",
        overview="No vector yet.",
        last_synced_at=datetime.utcnow(),
    )
    db_session.add(title)
    await db_session.flush()

    token = await _register_and_token(client)
    response = await client.get(
        f"/titles/{title.id}/similar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["items"] == []
