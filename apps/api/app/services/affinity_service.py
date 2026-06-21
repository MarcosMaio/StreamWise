from collections import defaultdict
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.embedding import UserStreamingAffinity
from app.models.interaction import Interaction
from app.models.provider import StreamingProvider, TitleStreamingProvider
from app.schemas.affinity import StreamingAffinity
from app.services.catalog_service import COUNTRY_CODE


class AffinityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def recompute_for_user(self, user_id: UUID) -> None:
        result = await self.db.execute(
            select(Interaction)
            .where(Interaction.user_id == user_id, Interaction.event_type == "like")
            .options(
                selectinload(Interaction.title)
                .selectinload(Title.streaming_providers)
                .selectinload(TitleStreamingProvider.provider)
            )
        )
        likes = result.scalars().unique().all()
        if not likes:
            return

        provider_counts: dict[UUID, int] = defaultdict(int)
        for interaction in likes:
            if interaction.title is None:
                continue
            for link in interaction.title.streaming_providers:
                if link.country_code != COUNTRY_CODE or link.availability_type != "flatrate":
                    continue
                provider_counts[link.provider_id] += 1

        total_likes = len(likes)
        if total_likes == 0 or not provider_counts:
            return

        raw_scores = {
            provider_id: count / total_likes for provider_id, count in provider_counts.items()
        }
        score_sum = sum(raw_scores.values())
        if score_sum <= 0:
            return

        await self.db.execute(
            delete(UserStreamingAffinity).where(UserStreamingAffinity.user_id == user_id)
        )

        for provider_id, raw_score in raw_scores.items():
            self.db.add(
                UserStreamingAffinity(
                    user_id=user_id,
                    provider_id=provider_id,
                    score=raw_score / score_sum,
                )
            )

    async def list_for_user(self, user_id: UUID) -> list[StreamingAffinity]:
        result = await self.db.execute(
            select(UserStreamingAffinity, StreamingProvider)
            .join(StreamingProvider, StreamingProvider.id == UserStreamingAffinity.provider_id)
            .where(UserStreamingAffinity.user_id == user_id)
            .order_by(UserStreamingAffinity.score.desc())
        )
        rows = result.all()
        return [
            StreamingAffinity(
                provider_id=affinity.provider_id,
                provider_name=provider.name,
                score=affinity.score,
            )
            for affinity, provider in rows
        ]
