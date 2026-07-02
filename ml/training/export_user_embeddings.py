#!/usr/bin/env python3
"""Export trained user embeddings into user_embeddings.model_vector.

The Two-Tower model learns a user embedding lookup table during training, but
only item embeddings were previously written back to the DB. Without user
vectors in user_embeddings.model_vector, _build_user_model_vector() in
recommendation_service.py always falls back to averaging liked titles'
item vectors — a reasonable proxy but not the actual learned representation.

This script bridges that gap: it reads the trained model.keras and a
user_id_map.json (UUID string → training integer ID), extracts each
platform user's 64-dim vector from the user embedding layer via a forward
pass, and upserts it into user_embeddings.model_vector.

Only StreamWise platform users (those with UUIDs in user_id_map.json) are
written. MovieLens-only users have no DB row and are silently skipped.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from uuid import UUID

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from app.config import get_settings  # noqa: E402
from app.models.embedding import UserEmbedding  # noqa: E402
from app.models.user import User  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def extract_user_vectors(
    model_path: Path,
    user_map: dict[str, int],
) -> dict[str, list[float]]:
    """Return {uuid_str: [float * 64]} for every user in user_map."""
    import tensorflow as tf

    model = tf.keras.models.load_model(model_path)
    user_embedding_layer = model.get_layer("user_embedding")

    result: dict[str, list[float]] = {}
    for uuid_str, int_id in user_map.items():
        vector = user_embedding_layer(np.array([int_id], dtype=np.int32)).numpy()[0]
        result[uuid_str] = vector.tolist()

    logger.info("Extracted vectors for %d platform users", len(result))
    return result


async def upsert_user_embeddings(vectors: dict[str, list[float]]) -> int:
    """Write user vectors into user_embeddings.model_vector (upsert)."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.orm import selectinload

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    updated = 0
    async with session_factory() as session:
        for uuid_str, vector in vectors.items():
            try:
                user_id = UUID(uuid_str)
            except ValueError:
                logger.warning("Skipping invalid UUID: %s", uuid_str)
                continue

            user = await session.get(User, user_id)
            if user is None:
                continue

            result = await session.execute(
                select(UserEmbedding).where(UserEmbedding.user_id == user_id)
            )
            embedding = result.scalar_one_or_none()

            if embedding is None:
                embedding = UserEmbedding(user_id=user_id, model_vector=vector)
                session.add(embedding)
            else:
                embedding.model_vector = vector

            updated += 1

        await session.commit()

    await engine.dispose()
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Export user embeddings to PostgreSQL")
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--user-map", type=Path, required=True)
    args = parser.parse_args()

    model_path = args.artifact_dir / "model.keras"
    if not model_path.exists():
        raise SystemExit(f"Missing {model_path}. Train the model first.")
    if not args.user_map.exists():
        raise SystemExit(f"Missing {args.user_map}. Run export_platform_interactions first.")

    with args.user_map.open() as fh:
        user_map: dict[str, int] = json.load(fh)

    if not user_map:
        logger.info("user_id_map is empty — no platform users to export")
        return

    vectors = extract_user_vectors(model_path, user_map)
    updated = asyncio.run(upsert_user_embeddings(vectors))
    logger.info("Updated model_vector for %d users", updated)


if __name__ == "__main__":
    main()
