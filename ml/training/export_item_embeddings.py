#!/usr/bin/env python3
"""Export trained item embeddings into title_embeddings.model_vector."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from app.config import get_settings
from app.models.embedding import TitleEmbedding
from app.models.title import Title

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_item_embeddings(path: Path) -> dict[int, list[float]]:
    payload = json.loads(path.read_text())
    return {int(key): value for key, value in payload.items()}


async def export_to_database(
    embeddings: dict[int, list[float]],
    *,
    fallback_dim: int = 64,
) -> int:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    updated = 0
    async with session_factory() as session:
        result = await session.execute(
            select(Title).where(Title.movielens_id.is_not(None)).options(selectinload(Title.embedding))
        )
        titles = result.scalars().all()

        for title in titles:
            vector = embeddings.get(title.movielens_id)
            if vector is None:
                continue

            if len(vector) != fallback_dim:
                logger.warning("Skipping movielens_id=%s due to dim mismatch", title.movielens_id)
                continue

            if title.embedding is None:
                logger.debug("Skipping title_id=%s without content embedding", title.id)
                continue

            title.embedding.model_vector = vector
            updated += 1

        await session.commit()

    await engine.dispose()
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Export item embeddings to PostgreSQL")
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("ml/artifacts/two_tower/v1"),
    )
    args = parser.parse_args()

    embeddings_path = args.artifact_dir / "item_embeddings.json"
    if not embeddings_path.exists():
        raise SystemExit(f"Missing {embeddings_path}. Train the model first.")

    embeddings = load_item_embeddings(embeddings_path)
    updated = asyncio.run(export_to_database(embeddings))
    logger.info("Updated model_vector for %d titles", updated)


if __name__ == "__main__":
    main()
