import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.embedding import TitleEmbedding, UserEmbedding
from app.models.interaction import Interaction
from app.models.provider import TitleStreamingProvider
from app.models.title import Genre, Title, TitleGenre
from app.models.user import User
from app.schemas.context import SessionContext
from app.schemas.recommendation import RecommendationItem, RecommendationListResponse
from app.services.bandit_service import BanditService
from app.services.catalog_service import CatalogService, COUNTRY_CODE
from app.services.context_filter import apply_session_context
from app.services.explainability_service import ExplainabilityService
from app.services.mmr_reranker import mmr_rerank
from app.services.model_loader import ModelLoader
from app.services.parental_filter_service import ParentalFilterService

logger = logging.getLogger(__name__)

RETRIEVAL_LIMIT = 200
STREAMING_BOOST_ALPHA = 0.3


class RecommendationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.catalog = CatalogService(db)
        self.model_loader = ModelLoader(db)
        self.explainability = ExplainabilityService()
        self.settings = get_settings()
        self.parental = ParentalFilterService(db)
        self.bandit = BanditService(db)

    async def get_for_you(
        self,
        user: User,
        *,
        limit: int = 20,
        provider_ids: list[UUID] | None = None,
        context: SessionContext | None = None,
    ) -> RecommendationListResponse:
        limit = min(limit, 50)
        excluded = await self._get_excluded_title_ids(user.id)
        liked_ids = await self._get_liked_title_ids(user.id)
        genre_ids = [pref.genre_id for pref in user.preferences]
        user_genre_names = await self._get_user_genre_names(genre_ids)
        affinities = {row.provider_id: row.score for row in user.streaming_affinities}
        content_filter = await self.parental.load_for_user(user.id)

        model_available = await self.model_loader.is_model_available()
        candidates = await self._retrieve_candidates(
            user_id=user.id,
            liked_ids=liked_ids,
            genre_ids=genre_ids,
            excluded=excluded,
            provider_ids=provider_ids,
        )

        fallback_used = False
        if not candidates:
            fallback_used = True
            candidates = await self._trending_fallback(genre_ids, excluded, provider_ids)

        candidates = apply_session_context(candidates, context)
        candidates = self.parental.apply_to_titles(candidates, content_filter)

        user_model_vector, using_collaborative = await self._build_user_model_vector(user.id, liked_ids)
        user_content_vector = await self._build_user_content_vector(liked_ids)

        ranked = await self._rank_candidates(
            candidates,
            user_model_vector=user_model_vector,
            user_content_vector=user_content_vector,
            affinities=affinities,
        )

        ranked = mmr_rerank(ranked, limit=limit, lambda_param=self.settings.mmr_lambda)

        if not model_available and liked_ids:
            fallback_used = True

        items: list[RecommendationItem] = []
        for score, title in ranked[:limit]:
            content_similarity = None
            if user_content_vector and title.embedding and title.embedding.content_vector is not None:
                content_similarity = 1.0 - _cosine_distance(
                    user_content_vector, list(title.embedding.content_vector)
                )

            reason_tags = self.explainability.build_reason_tags(
                title,
                user_genre_names=user_genre_names,
                affinities=affinities,
                has_likes=bool(liked_ids),
                content_similarity=content_similarity,
                used_collaborative=using_collaborative,
            )
            items.append(
                RecommendationItem(
                    **self.catalog._to_summary(title).model_dump(),
                    score=score,
                    reason_tags=reason_tags,
                )
            )

        items = await self.bandit.inject_exploration(
            user.id,
            items,
            excluded=excluded,
            limit=limit,
        )

        if len(items) < limit and not liked_ids:
            extra = await self._cold_start_fill(
                genre_ids=genre_ids,
                excluded=excluded | {item.id for item in items},
                provider_ids=provider_ids,
                remaining=limit - len(items),
            )
            items.extend(extra)

        return RecommendationListResponse(items=items, fallback_used=fallback_used)

    async def _get_user_genre_names(self, genre_ids: list[UUID]) -> set[str]:
        if not genre_ids:
            return set()
        result = await self.db.execute(select(Genre.name).where(Genre.id.in_(genre_ids)))
        return set(result.scalars().all())

    async def _get_excluded_title_ids(self, user_id: UUID) -> set[UUID]:
        result = await self.db.execute(
            select(Interaction.title_id).where(
                Interaction.user_id == user_id,
                Interaction.event_type.in_(("watched", "dislike")),
            )
        )
        return set(result.scalars().all())

    async def _get_liked_title_ids(self, user_id: UUID) -> list[UUID]:
        result = await self.db.execute(
            select(Interaction.title_id).where(
                Interaction.user_id == user_id,
                Interaction.event_type == "like",
            )
        )
        return list(result.scalars().all())

    async def _retrieve_candidates(
        self,
        *,
        user_id: UUID,
        liked_ids: list[UUID],
        genre_ids: list[UUID],
        excluded: set[UUID],
        provider_ids: list[UUID] | None,
    ) -> list[Title]:
        if liked_ids:
            profile_vector = await self._build_user_content_vector(liked_ids)
            if profile_vector is not None:
                return await self._retrieve_by_content_vector(
                    profile_vector, excluded, provider_ids, RETRIEVAL_LIMIT
                )

        if genre_ids:
            return await self._retrieve_by_genres(genre_ids, excluded, provider_ids, RETRIEVAL_LIMIT)

        return await self._trending_fallback(genre_ids, excluded, provider_ids)

    async def _retrieve_by_content_vector(
        self,
        profile_vector: list[float],
        excluded: set[UUID],
        provider_ids: list[UUID] | None,
        limit: int,
    ) -> list[Title]:
        query = (
            select(Title)
            .join(TitleEmbedding, Title.id == TitleEmbedding.title_id)
            .options(
                selectinload(Title.title_genres).selectinload(TitleGenre.genre),
                selectinload(Title.streaming_providers).selectinload(
                    TitleStreamingProvider.provider
                ),
                selectinload(Title.embedding),
            )
            .order_by(TitleEmbedding.content_vector.cosine_distance(profile_vector))
            .limit(limit)
        )

        if excluded:
            query = query.where(Title.id.notin_(excluded))

        if provider_ids:
            query = query.join(
                TitleStreamingProvider,
                TitleStreamingProvider.title_id == Title.id,
            ).where(
                TitleStreamingProvider.provider_id.in_(provider_ids),
                TitleStreamingProvider.country_code == COUNTRY_CODE,
            )

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    async def _retrieve_by_genres(
        self,
        genre_ids: list[UUID],
        excluded: set[UUID],
        provider_ids: list[UUID] | None,
        limit: int,
    ) -> list[Title]:
        query = (
            select(Title)
            .join(TitleGenre, TitleGenre.title_id == Title.id)
            .where(TitleGenre.genre_id.in_(genre_ids))
            .options(
                selectinload(Title.title_genres).selectinload(TitleGenre.genre),
                selectinload(Title.streaming_providers).selectinload(
                    TitleStreamingProvider.provider
                ),
                selectinload(Title.embedding),
            )
            .order_by(Title.tmdb_popularity.desc())
            .limit(limit)
        )

        if excluded:
            query = query.where(Title.id.notin_(excluded))

        if provider_ids:
            query = query.join(
                TitleStreamingProvider,
                TitleStreamingProvider.title_id == Title.id,
            ).where(
                TitleStreamingProvider.provider_id.in_(provider_ids),
                TitleStreamingProvider.country_code == COUNTRY_CODE,
            )

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    async def _trending_fallback(
        self,
        genre_ids: list[UUID],
        excluded: set[UUID],
        provider_ids: list[UUID] | None,
    ) -> list[Title]:
        if genre_ids:
            titles = await self._retrieve_by_genres(
                genre_ids, excluded, provider_ids, RETRIEVAL_LIMIT
            )
            if titles:
                return titles

        query = (
            select(Title)
            .where(Title.is_trending.is_(True))
            .options(
                selectinload(Title.title_genres).selectinload(TitleGenre.genre),
                selectinload(Title.streaming_providers).selectinload(
                    TitleStreamingProvider.provider
                ),
                selectinload(Title.embedding),
            )
            .order_by(Title.tmdb_popularity.desc())
            .limit(RETRIEVAL_LIMIT)
        )

        if excluded:
            query = query.where(Title.id.notin_(excluded))

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    async def _build_user_content_vector(self, liked_ids: list[UUID]) -> list[float] | None:
        if not liked_ids:
            return None

        result = await self.db.execute(
            select(TitleEmbedding.content_vector).where(TitleEmbedding.title_id.in_(liked_ids))
        )
        vectors = [list(row[0]) for row in result.all()]
        return _mean_vector(vectors)

    async def _build_user_model_vector(
        self,
        user_id: UUID,
        liked_ids: list[UUID],
    ) -> tuple[list[float] | None, bool]:
        """Return (vector, is_learned) where is_learned=True means we used the
        actual Two-Tower user embedding (UserEmbedding.model_vector), not the
        fallback average of liked items' vectors. The caller uses is_learned to
        decide whether to show the 'similar taste' collaborative reason tag.
        """
        user_embedding = await self.db.get(UserEmbedding, user_id)
        if user_embedding and user_embedding.model_vector is not None:
            return list(user_embedding.model_vector), True

        if not liked_ids:
            return None, False

        result = await self.db.execute(
            select(TitleEmbedding.model_vector).where(
                TitleEmbedding.title_id.in_(liked_ids),
                TitleEmbedding.model_vector.is_not(None),
            )
        )
        vectors = [list(row[0]) for row in result.all()]
        return _mean_vector(vectors), False

    async def _rank_candidates(
        self,
        candidates: list[Title],
        *,
        user_model_vector: list[float] | None,
        user_content_vector: list[float] | None,
        affinities: dict[UUID, float],
    ) -> list[tuple[float, Title]]:
        ranked: list[tuple[float, Title]] = []

        for title in candidates:
            embedding = title.embedding
            base_score = title.tmdb_popularity / 100.0

            if user_model_vector and embedding and embedding.model_vector is not None:
                base_score = _dot(user_model_vector, list(embedding.model_vector))
            elif user_content_vector and embedding and embedding.content_vector is not None:
                base_score = 1.0 - _cosine_distance(
                    user_content_vector, list(embedding.content_vector)
                )

            provider_boost = _provider_boost(title, affinities)
            final_score = base_score * (1.0 + STREAMING_BOOST_ALPHA * provider_boost)
            ranked.append((final_score, title))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return ranked

    async def _cold_start_fill(
        self,
        *,
        genre_ids: list[UUID],
        excluded: set[UUID],
        provider_ids: list[UUID] | None,
        remaining: int,
    ) -> list[RecommendationItem]:
        if remaining <= 0 or not genre_ids:
            return []

        titles = await self._retrieve_by_genres(
            genre_ids, excluded, provider_ids, remaining
        )
        return [
            RecommendationItem(
                **self.catalog._to_summary(title).model_dump(),
                score=title.tmdb_popularity / 100.0,
            )
            for title in titles
        ]


def _mean_vector(vectors: list[list[float]]) -> list[float] | None:
    if not vectors:
        return None
    dim = len(vectors[0])
    sums = [0.0] * dim
    for vector in vectors:
        for index, value in enumerate(vector):
            sums[index] += value
    count = len(vectors)
    return [value / count for value in sums]


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=False))


def _cosine_distance(left: list[float], right: list[float]) -> float:
    dot = _dot(left, right)
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 1.0
    return 1.0 - (dot / (left_norm * right_norm))


def _provider_boost(title: Title, affinities: dict[UUID, float]) -> float:
    if not affinities:
        return 0.0

    scores = [
        affinities[link.provider_id]
        for link in title.streaming_providers
        if link.country_code == COUNTRY_CODE
        and link.availability_type == "flatrate"
        and link.provider_id in affinities
    ]
    return max(scores) if scores else 0.0
