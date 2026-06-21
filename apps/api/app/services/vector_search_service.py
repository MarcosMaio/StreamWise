import logging
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.embedding import TitleEmbedding
from app.models.provider import TitleStreamingProvider
from app.models.title import Title, TitleGenre
from app.schemas.title import TitleListResponse
from app.services.catalog_service import CatalogService

logger = logging.getLogger(__name__)


class VectorSearchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.catalog = CatalogService(db)

    async def find_similar_titles(
        self,
        title_id: UUID,
        *,
        limit: int = 20,
        provider_ids: list[UUID] | None = None,
    ) -> TitleListResponse:
        source = await self.db.get(TitleEmbedding, title_id)
        if source is None:
            return TitleListResponse(items=[], total=0)

        query = (
            select(Title)
            .join(TitleEmbedding, Title.id == TitleEmbedding.title_id)
            .where(Title.id != title_id)
            .options(
                selectinload(Title.title_genres).selectinload(TitleGenre.genre),
                selectinload(Title.streaming_providers).selectinload(
                    TitleStreamingProvider.provider
                ),
            )
            .order_by(TitleEmbedding.content_vector.cosine_distance(source.content_vector))
            .limit(min(limit, 50))
        )

        if provider_ids:
            query = query.join(
                TitleStreamingProvider,
                TitleStreamingProvider.title_id == Title.id,
            ).where(
                TitleStreamingProvider.provider_id.in_(provider_ids),
                TitleStreamingProvider.country_code == "BR",
            )

        result = await self.db.execute(query)
        titles = result.scalars().unique().all()
        stale, note = await self.catalog.get_stale_data_info()
        items = [self.catalog._to_summary(title) for title in titles]
        return TitleListResponse(items=items, total=len(items), stale_data=stale, availability_note=note)

    @staticmethod
    async def rebuild_ivfflat_index(db: AsyncSession, lists: int = 100) -> None:
        await db.execute(text("DROP INDEX IF EXISTS ix_title_embeddings_content_vector"))
        await db.execute(
            text(
                f"""
                CREATE INDEX ix_title_embeddings_content_vector
                ON title_embeddings USING ivfflat (content_vector vector_cosine_ops)
                WITH (lists = {int(lists)})
                """
            )
        )
        logger.info("Rebuilt IVFFlat index on title_embeddings.content_vector (lists=%d)", lists)
