import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.models.embedding import TitleEmbedding
from app.models.title import Title, TitleGenre
from app.services.embedding_generator import EmbeddingGenerator

logger = logging.getLogger(__name__)


class ContentEmbeddingService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self._generator: EmbeddingGenerator | None = None

    def _get_generator(self) -> EmbeddingGenerator:
        if self._generator is None:
            self._generator = EmbeddingGenerator(self.settings.embedding_model)
        return self._generator

    async def upsert_title_embedding(self, title_id: UUID) -> bool:
        title = await self._load_title(title_id)
        if title is None:
            return False
        return await self._upsert_for_title(title)

    async def upsert_titles(self, titles: list[Title]) -> int:
        embedded = 0
        for title in titles:
            if await self._upsert_for_title(title):
                embedded += 1
        return embedded

    async def _load_title(self, title_id: UUID) -> Title | None:
        result = await self.db.execute(
            select(Title)
            .where(Title.id == title_id)
            .options(selectinload(Title.title_genres).selectinload(TitleGenre.genre))
        )
        return result.scalar_one_or_none()

    async def _upsert_for_title(self, title: Title) -> bool:
        if not title.overview or not title.overview.strip():
            return False

        genres = [link.genre.name for link in title.title_genres if link.genre]
        text = EmbeddingGenerator.build_title_text(title.title, title.overview, genres)

        try:
            vector = self._get_generator().encode(text)
        except RuntimeError as exc:
            logger.warning("Skipping embedding for title_id=%s: %s", title.id, exc)
            return False
        except Exception:
            logger.exception("Failed to generate embedding for title_id=%s", title.id)
            return False

        existing = await self.db.get(TitleEmbedding, title.id)
        if existing is None:
            self.db.add(TitleEmbedding(title_id=title.id, content_vector=vector))
        else:
            existing.content_vector = vector

        await self.db.flush()
        return True
