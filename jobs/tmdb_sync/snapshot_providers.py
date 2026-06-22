"""Snapshot current provider availability for catalog diff."""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import date
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from app.config import get_settings
from app.services.catalog_change_service import CatalogChangeService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def run_snapshot(snapshot_date: date | None = None) -> int:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        service = CatalogChangeService(session)
        count = await service.snapshot_current_providers(snapshot_date=snapshot_date)
        logger.info("Saved provider snapshot rows=%d date=%s", count, snapshot_date or date.today())
        return count

    await engine.dispose()


def main() -> None:
    asyncio.run(run_snapshot())


if __name__ == "__main__":
    main()
