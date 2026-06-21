"""TMDB catalog sync — trending, new releases, BR streaming providers."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))
if Path("/app/app").exists():
    sys.path.insert(0, "/app")

from app.config import get_settings
from app.services.catalog_service import CatalogService
from app.services.content_embedding_service import ContentEmbeddingService
from app.services.tmdb_client import TMDBClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

STATUS_DIR = Path(os.environ.get("SYNC_STATUS_DIR", Path(__file__).resolve().parent))
STATUS_DIR.mkdir(parents=True, exist_ok=True)
STATUS_FILE = STATUS_DIR / "last_sync_status.json"


@dataclass
class SyncRunResult:
    started_at: str
    finished_at: str | None = None
    success: bool = False
    duration_seconds: float = 0.0
    trending_movies: int = 0
    trending_series: int = 0
    new_movies: int = 0
    new_series: int = 0
    providers_synced: int = 0
    embeddings_generated: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def titles_synced(self) -> int:
        return self.trending_movies + self.trending_series + self.new_movies + self.new_series


def _write_status(result: SyncRunResult) -> None:
    import json

    STATUS_FILE.write_text(json.dumps(asdict(result), indent=2))
    logger.info(
        "sync_health status=%s titles=%d providers=%d duration=%.1fs errors=%d",
        "success" if result.success else "failure",
        result.titles_synced,
        result.providers_synced,
        result.duration_seconds,
        len(result.errors),
    )


async def _sync_list(
    session: AsyncSession,
    service: CatalogService,
    items: list[dict],
    media_type: str,
    *,
    is_trending: bool,
    is_new_release: bool,
) -> list:
    synced = []
    for item in items:
        title = await service.upsert_title_from_tmdb(
            item,
            "series" if media_type == "tv" else "movie",
            is_trending=is_trending,
            is_new_release=is_new_release,
        )
        synced.append(title)
    await session.flush()
    return synced


async def run_sync(pages: int = 1) -> SyncRunResult:
    started = datetime.now(UTC)
    result = SyncRunResult(started_at=started.isoformat())
    timer = time.monotonic()

    settings = get_settings()
    if not settings.tmdb_api_key:
        result.errors.append("TMDB_API_KEY is not configured")
        result.finished_at = datetime.now(UTC).isoformat()
        result.duration_seconds = time.monotonic() - timer
        _write_status(result)
        return result

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    tmdb = TMDBClient(settings)

    try:
        async with session_factory() as session:
            service = CatalogService(session, tmdb)
            await service.clear_catalog_flags()

            all_titles = []

            for page in range(1, pages + 1):
                trending_movies = await tmdb.get_trending("movie", page)
                titles = await _sync_list(
                    session,
                    service,
                    trending_movies.get("results") or [],
                    "movie",
                    is_trending=True,
                    is_new_release=False,
                )
                result.trending_movies += len(titles)
                all_titles.extend(titles)

                trending_tv = await tmdb.get_trending("tv", page)
                titles = await _sync_list(
                    session,
                    service,
                    trending_tv.get("results") or [],
                    "tv",
                    is_trending=True,
                    is_new_release=False,
                )
                result.trending_series += len(titles)
                all_titles.extend(titles)

                now_playing = await tmdb.get_now_playing(page)
                titles = await _sync_list(
                    session,
                    service,
                    now_playing.get("results") or [],
                    "movie",
                    is_trending=False,
                    is_new_release=True,
                )
                result.new_movies += len(titles)
                all_titles.extend(titles)

                on_the_air = await tmdb.get_on_the_air(page)
                titles = await _sync_list(
                    session,
                    service,
                    on_the_air.get("results") or [],
                    "tv",
                    is_trending=False,
                    is_new_release=True,
                )
                result.new_series += len(titles)
                all_titles.extend(titles)

            seen_ids = set()
            unique_titles = []
            for title in all_titles:
                if title.id not in seen_ids:
                    seen_ids.add(title.id)
                    unique_titles.append(title)

            for title in unique_titles:
                try:
                    await service.sync_watch_providers(title)
                    result.providers_synced += 1
                except Exception as exc:
                    msg = f"providers tmdb_id={title.tmdb_id}: {exc}"
                    logger.warning(msg)
                    result.errors.append(msg)

            try:
                embedding_service = ContentEmbeddingService(session)
                embedded = 0
                for title in unique_titles:
                    if await embedding_service.upsert_title_embedding(title.id):
                        embedded += 1
                result.embeddings_generated = embedded
                logger.info("Generated embeddings for %d titles", result.embeddings_generated)
            except Exception as exc:
                msg = f"embeddings: {exc}"
                logger.warning(msg)
                result.errors.append(msg)

            await session.commit()
            result.success = len(result.errors) == 0 or result.titles_synced > 0
    except Exception as exc:
        logger.exception("Catalog sync failed")
        result.errors.append(str(exc))
        result.success = False
    finally:
        await engine.dispose()

    result.finished_at = datetime.now(UTC).isoformat()
    result.duration_seconds = time.monotonic() - timer
    _write_status(result)
    return result


def main() -> None:
    result = asyncio.run(run_sync())
    if not result.success:
        logger.error("Sync completed with errors: %s", result.errors)
        sys.exit(1)
    logger.info(
        "Sync complete: %d titles, %d providers in %.1fs",
        result.titles_synced,
        result.providers_synced,
        result.duration_seconds,
    )


if __name__ == "__main__":
    main()
