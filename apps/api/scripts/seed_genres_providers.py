import asyncio
import logging
import sys
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.models.provider import StreamingProvider
from app.models.title import Genre

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TMDB_GENRES = [
    (28, "Action"),
    (12, "Adventure"),
    (16, "Animation"),
    (35, "Comedy"),
    (80, "Crime"),
    (99, "Documentary"),
    (18, "Drama"),
    (10751, "Family"),
    (14, "Fantasy"),
    (36, "History"),
    (27, "Horror"),
    (10402, "Music"),
    (9648, "Mystery"),
    (10749, "Romance"),
    (878, "Science Fiction"),
    (10770, "TV Movie"),
    (53, "Thriller"),
    (10752, "War"),
    (37, "Western"),
    (10759, "Action & Adventure"),
    (10762, "Kids"),
    (10763, "News"),
    (10764, "Reality"),
    (10765, "Sci-Fi & Fantasy"),
    (10766, "Soap"),
    (10767, "Talk"),
    (10768, "War & Politics"),
]

BR_STREAMING_PROVIDERS = [
    (8, "Netflix", "/t/p/original/9A1AdMobwew5BxcAhy6JKXpO2V.jpg"),
    (119, "Amazon Prime Video", "/t/p/original/9A1AdMobwew5BxcAhy6JKXpO2V.jpg"),
    (337, "Disney Plus", "/t/p/original/dgPueyEdOgIlcBFqkoHChqXVCV.jpg"),
    (384, "HBO Max", "/t/p/original/aS2zvJWzUrEsnMFfwHN6JZYm5R6.jpg"),
    (350, "Apple TV Plus", "/t/p/original/peURlLlr8jggOwK53fJxhmIi4g.jpg"),
    (531, "Paramount Plus", "/t/p/original/piAHTgw03BLu93A4UbDZI6B2Vj.jpg"),
    (283, "Crunchyroll", "/t/p/original/8nIg2ndg9H4000f5X2BeM27XJBx.jpg"),
]


async def seed(session: AsyncSession) -> None:
    existing_genres = (await session.execute(select(Genre))).scalars().all()
    if not existing_genres:
        for tmdb_id, name in TMDB_GENRES:
            session.add(Genre(id=uuid.uuid4(), name=name, tmdb_genre_id=tmdb_id))
        logger.info("Seeded %d genres", len(TMDB_GENRES))
    else:
        logger.info("Genres already seeded (%d rows)", len(existing_genres))

    existing_providers = (await session.execute(select(StreamingProvider))).scalars().all()
    if not existing_providers:
        for tmdb_id, name, logo in BR_STREAMING_PROVIDERS:
            session.add(
                StreamingProvider(
                    id=uuid.uuid4(),
                    tmdb_provider_id=tmdb_id,
                    name=name,
                    logo_path=logo,
                )
            )
        logger.info("Seeded %d streaming providers", len(BR_STREAMING_PROVIDERS))
    else:
        logger.info("Streaming providers already seeded (%d rows)", len(existing_providers))

    await session.commit()


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
