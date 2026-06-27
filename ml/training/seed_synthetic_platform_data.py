#!/usr/bin/env python3
"""Seed synthetic multi-user taste-cluster interactions on the live catalog.

The current TMDB-synced catalog has almost no overlap with MovieLens
latest-small (recent releases vs. pre-2018 movies), so merging real platform
likes with MovieLens ratings would carry essentially no shared items. This
script instead backfills `titles.movielens_id` as a plain item-index (reusing
the existing bridge column purely as the integer key the Two-Tower training
code expects) and generates synthetic users with genre-correlated taste
clusters so the model has genuine collaborative co-occurrence structure to
learn from on the real catalog.

Writes real rows to `users` and `interactions`, then exports a ratings
parquet (userId, movieId, rating) for `train_two_tower.py --ratings-path`.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from app.config import get_settings  # noqa: E402
from app.models.interaction import Interaction  # noqa: E402
from app.models.title import Genre, Title, TitleGenre  # noqa: E402
from app.models.user import User  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MOVIELENS_ID_OFFSET = 1_000_000  # clear of any real MovieLens item IDs
NUM_USERS = 40
SEED = 42


async def backfill_movielens_ids(session: AsyncSession) -> dict[uuid.UUID, int]:
    result = await session.execute(select(Title).where(Title.movielens_id.is_(None)))
    titles = result.scalars().all()

    max_result = await session.execute(select(Title.movielens_id))
    existing_ids = [v for (v,) in max_result.all() if v is not None]
    next_id = max(existing_ids, default=MOVIELENS_ID_OFFSET - 1) + 1

    mapping: dict[uuid.UUID, int] = {}
    for offset, title in enumerate(titles):
        item_id = next_id + offset
        await session.execute(
            update(Title).where(Title.id == title.id).values(movielens_id=item_id)
        )
        mapping[title.id] = item_id
    await session.commit()
    logger.info("Backfilled movielens_id for %d titles", len(mapping))
    return mapping


async def build_genre_clusters(session: AsyncSession) -> dict[str, list[uuid.UUID]]:
    result = await session.execute(
        select(Genre.name, TitleGenre.title_id).join(TitleGenre, TitleGenre.genre_id == Genre.id)
    )
    by_genre: dict[str, list[uuid.UUID]] = {}
    for name, title_id in result.all():
        by_genre.setdefault(name, []).append(title_id)

    top_genres = sorted(by_genre.items(), key=lambda kv: len(kv[1]), reverse=True)[:4]
    clusters = {name: title_ids for name, title_ids in top_genres}
    logger.info("Taste clusters: %s", {k: len(v) for k, v in clusters.items()})
    return clusters


async def create_synthetic_users(session: AsyncSession, n: int) -> list[User]:
    emails = [f"seed-user-{i:03d}@seed.streamwise.local" for i in range(n)]
    result = await session.execute(select(User).where(User.email.in_(emails)))
    existing = {user.email: user for user in result.scalars().all()}

    users = []
    created = 0
    for email in emails:
        if email in existing:
            users.append(existing[email])
            continue
        user = User(
            email=email,
            display_name=email.split("@")[0],
            country_code="BR",
            onboarding_complete=True,
        )
        session.add(user)
        users.append(user)
        created += 1
    await session.flush()
    logger.info("Reused %d existing + created %d new synthetic users", len(existing), created)
    return users


def assign_clusters(users: list[User], cluster_names: list[str], rng: random.Random) -> dict[uuid.UUID, str]:
    assignment = {}
    for user in users:
        assignment[user.id] = rng.choice(cluster_names)
    return assignment


async def generate_interactions(
    session: AsyncSession,
    users: list[User],
    clusters: dict[str, list[uuid.UUID]],
    rng: random.Random,
) -> int:
    cluster_names = list(clusters.keys())
    all_title_ids = {tid for ids in clusters.values() for tid in ids}
    user_cluster = assign_clusters(users, cluster_names, rng)

    user_ids = [user.id for user in users]
    existing_result = await session.execute(
        select(Interaction.user_id).where(Interaction.user_id.in_(user_ids))
    )
    users_with_interactions = {row[0] for row in existing_result.all()}

    inserted = 0
    for user in users:
        if user.id in users_with_interactions:
            continue
        primary = user_cluster[user.id]
        in_cluster = set(clusters[primary])
        out_cluster = list(all_title_ids - in_cluster)

        seen_titles: set[uuid.UUID] = set()

        for title_id in in_cluster:
            if rng.random() > 0.65:
                continue
            roll = rng.random()
            if roll < 0.7:
                event_type, rating = "like", None
            elif roll < 0.85:
                event_type, rating = "rating", float(rng.choice([4.0, 5.0]))
            else:
                continue
            session.add(
                Interaction(
                    user_id=user.id,
                    title_id=title_id,
                    event_type=event_type,
                    rating=rating,
                )
            )
            seen_titles.add(title_id)
            inserted += 1

        noise_sample = rng.sample(out_cluster, k=min(6, len(out_cluster)))
        for title_id in noise_sample:
            if title_id in seen_titles:
                continue
            roll = rng.random()
            if roll < 0.5:
                event_type, rating = "dislike", None
            elif roll < 0.7:
                event_type, rating = "rating", float(rng.choice([1.0, 2.0]))
            else:
                continue
            session.add(
                Interaction(
                    user_id=user.id,
                    title_id=title_id,
                    event_type=event_type,
                    rating=rating,
                )
            )
            inserted += 1

    await session.commit()
    logger.info("Inserted %d synthetic interactions", inserted)
    return inserted


def _interaction_to_rating(event_type: str, rating: float | None) -> float | None:
    if event_type == "like":
        return 5.0
    if event_type == "dislike":
        return 1.0
    if event_type == "rating" and rating is not None:
        return rating
    return None


async def export_ratings_parquet(session: AsyncSession, output_path: Path) -> int:
    result = await session.execute(
        select(Interaction)
        .join(Title, Title.id == Interaction.title_id)
        .where(Title.movielens_id.is_not(None))
        .options(selectinload(Interaction.title))
        .order_by(Interaction.created_at)
    )
    interactions = result.scalars().unique().all()

    # Small sequential range: train_two_tower.py sizes the user embedding
    # table by max(raw_id + 1, config_vocab_size), not a remapped dense
    # index, so a large offset here blows up the embedding table memory
    # for no benefit (this run never merges with real MovieLens user IDs).
    user_offset = 0
    user_map: dict[uuid.UUID, int] = {}
    rows = []
    for interaction in interactions:
        if interaction.title is None or interaction.title.movielens_id is None:
            continue
        rating_value = _interaction_to_rating(interaction.event_type, interaction.rating)
        if rating_value is None:
            continue
        if interaction.user_id not in user_map:
            user_map[interaction.user_id] = user_offset + len(user_map)
        rows.append(
            {
                "userId": user_map[interaction.user_id],
                "movieId": int(interaction.title.movielens_id),
                "rating": rating_value,
                "timestamp": int(interaction.created_at.timestamp()),
                "source": "platform",
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(output_path, index=False)
    logger.info("Exported %d rows to %s (%d distinct users)", len(rows), output_path, len(user_map))
    return len(rows)


async def main_async(output_path: Path) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    rng = random.Random(SEED)

    async with session_factory() as session:
        await backfill_movielens_ids(session)
        clusters = await build_genre_clusters(session)
        users = await create_synthetic_users(session, NUM_USERS)
        await generate_interactions(session, users, clusters, rng)
        await export_ratings_parquet(session, output_path)

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed synthetic platform interactions for Two-Tower training")
    parser.add_argument(
        "--output-path",
        type=Path,
        default=REPO_ROOT / "ml/artifacts/platform/synthetic_ratings.parquet",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args.output_path))


if __name__ == "__main__":
    main()
