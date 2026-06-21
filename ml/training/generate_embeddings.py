#!/usr/bin/env python3
"""Batch-generate synopsis embeddings and rebuild the pgvector IVFFlat index."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from app.config import get_settings
from app.models.title import Title, TitleGenre
from app.services.content_embedding_service import ContentEmbeddingService
from app.services.vector_search_service import VectorSearchService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def batch_embed_all(session: AsyncSession, *, rebuild_index: bool, lists: int) -> int:
    result = await session.execute(
        select(Title)
        .where(Title.overview.is_not(None), Title.overview != "")
        .options(selectinload(Title.title_genres).selectinload(TitleGenre.genre))
        .order_by(Title.title)
    )
    titles = result.scalars().unique().all()
    logger.info("Embedding %d titles with overview text", len(titles))

    service = ContentEmbeddingService(session)
    embedded = await service.upsert_titles(titles)

    if rebuild_index and embedded > 0:
        await VectorSearchService.rebuild_ivfflat_index(session, lists=lists)

    await session.commit()
    return embedded


async def main(rebuild_index: bool, lists: int) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        embedded = await batch_embed_all(session, rebuild_index=rebuild_index, lists=lists)

    await engine.dispose()
    logger.info("Embedded %d titles", embedded)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate title content embeddings")
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Rebuild IVFFlat index after batch insert",
    )
    parser.add_argument(
        "--lists",
        type=int,
        default=100,
        help="IVFFlat lists parameter (default: 100)",
    )
    args = parser.parse_args()
    asyncio.run(main(rebuild_index=args.rebuild_index, lists=args.lists))
