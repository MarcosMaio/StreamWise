import logging
from uuid import UUID

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.embedding import TitleEmbedding
from app.models.provider import TitleStreamingProvider
from app.models.title import Title, TitleGenre
from app.schemas.title import TitleListResponse
from app.services.catalog_service import CatalogService
from app.services.embedding_generator import EmbeddingGenerator

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

    async def search_by_query(
        self,
        query: str,
        *,
        limit: int = 20,
        provider_ids: list[UUID] | None = None,
        genre_ids: list[UUID] | None = None,
    ) -> TitleListResponse:
        cleaned = query.strip()
        if not cleaned:
            return TitleListResponse(items=[], total=0)

        try:
            settings = get_settings()
            generator = EmbeddingGenerator(settings.embedding_model)
            vector = generator.encode(cleaned)
            results = await self._search_by_content_vector(
                vector,
                limit=limit,
                provider_ids=provider_ids,
                genre_ids=genre_ids,
            )
            if results.items:
                return results
        except Exception:
            logger.warning("Vector search unavailable for query=%r, using keyword fallback", cleaned)

        return await self._keyword_search(
            cleaned,
            limit=limit,
            provider_ids=provider_ids,
            genre_ids=genre_ids,
        )

    async def _search_by_content_vector(
        self,
        vector: list[float],
        *,
        limit: int,
        provider_ids: list[UUID] | None,
        genre_ids: list[UUID] | None,
    ) -> TitleListResponse:
        db_query = (
            select(Title)
            .join(TitleEmbedding, Title.id == TitleEmbedding.title_id)
            .options(
                selectinload(Title.title_genres).selectinload(TitleGenre.genre),
                selectinload(Title.streaming_providers).selectinload(
                    TitleStreamingProvider.provider
                ),
            )
            .order_by(TitleEmbedding.content_vector.cosine_distance(vector))
            .limit(min(limit, 50))
        )
        db_query = self.catalog._apply_genre_filter(db_query, genre_ids)
        db_query = self.catalog._apply_provider_filter(db_query, provider_ids)

        result = await self.db.execute(db_query)
        titles = result.scalars().unique().all()
        stale, note = await self.catalog.get_stale_data_info()
        items = [self.catalog._to_summary(title) for title in titles]
        return TitleListResponse(items=items, total=len(items), stale_data=stale, availability_note=note)

    async def _keyword_search(
        self,
        query: str,
        *,
        limit: int,
        provider_ids: list[UUID] | None,
        genre_ids: list[UUID] | None,
    ) -> TitleListResponse:
        terms = [term for term in query.split() if term]
        if not terms:
            return TitleListResponse(items=[], total=0)

        text_filters = []
        for term in terms:
            pattern = f"%{term}%"
            text_filters.append(Title.title.ilike(pattern))
            text_filters.append(Title.overview.ilike(pattern))

        db_query = (
            select(Title)
            .where(or_(*text_filters))
            .options(
                selectinload(Title.title_genres).selectinload(TitleGenre.genre),
                selectinload(Title.streaming_providers).selectinload(
                    TitleStreamingProvider.provider
                ),
            )
            .order_by(Title.tmdb_popularity.desc())
            .limit(min(limit, 50))
        )
        db_query = self.catalog._apply_genre_filter(db_query, genre_ids)
        db_query = self.catalog._apply_provider_filter(db_query, provider_ids)

        result = await self.db.execute(db_query)
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
