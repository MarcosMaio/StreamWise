import random
import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.p2 import BanditEvent
from app.models.provider import TitleStreamingProvider
from app.models.title import Title, TitleGenre
from app.schemas.recommendation import RecommendationItem

EXPLORATION_RATIO = 0.15


class BanditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def inject_exploration(
        self,
        user_id: UUID,
        items: list[RecommendationItem],
        *,
        excluded: set[UUID],
        limit: int,
    ) -> list[RecommendationItem]:
        if not items or limit <= 0:
            return items

        target = max(1, int(round(limit * EXPLORATION_RATIO)))
        current_ids = {item.id for item in items}
        exploration_titles = await self._sample_exploration_titles(
            exclude=excluded | current_ids,
            count=target,
        )
        if not exploration_titles:
            return items

        merged = list(items[:limit])
        for title in exploration_titles:
            if len(merged) >= limit:
                break
            slot = random.randrange(min(len(merged), limit))
            merged.insert(
                slot,
                RecommendationItem(
                    **title,
                    score=0.0,
                    reason_tags=["Explore something new"],
                    exploration=True,
                ),
            )
            merged = merged[:limit]

        await self._log_impressions(user_id, merged)
        return merged

    async def _sample_exploration_titles(
        self,
        *,
        exclude: set[UUID],
        count: int,
    ) -> list[dict]:
        query = (
            select(Title)
            .options(
                selectinload(Title.title_genres).selectinload(TitleGenre.genre),
                selectinload(Title.streaming_providers).selectinload(
                    TitleStreamingProvider.provider
                ),
            )
            .order_by(func.random())
            .limit(count * 3)
        )
        if exclude:
            query = query.where(Title.id.notin_(exclude))

        result = await self.db.execute(query)
        titles = result.scalars().unique().all()
        from app.services.catalog_service import CatalogService

        catalog = CatalogService(self.db)
        return [catalog._to_summary(title).model_dump() for title in titles[:count]]

    async def _log_impressions(self, user_id: UUID, items: list[RecommendationItem]) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        for item in items:
            self.db.add(
                BanditEvent(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    title_id=item.id,
                    event_type="impression",
                    is_exploration=getattr(item, "exploration", False),
                    created_at=now,
                )
            )
        await self.db.flush()

    async def log_click(self, user_id: UUID, title_id: UUID, *, is_exploration: bool) -> None:
        self.db.add(
            BanditEvent(
                id=uuid.uuid4(),
                user_id=user_id,
                title_id=title_id,
                event_type="click",
                is_exploration=is_exploration,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        await self.db.commit()
