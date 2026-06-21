from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import Interaction
from app.models.title import Title


class TitleAggregateService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def refresh_title_aggregates(self, title_id: UUID) -> None:
        like_count = await self.db.scalar(
            select(func.count())
            .select_from(Interaction)
            .where(Interaction.title_id == title_id, Interaction.event_type == "like")
        )
        rating_stats = await self.db.execute(
            select(func.avg(Interaction.rating), func.count())
            .select_from(Interaction)
            .where(
                Interaction.title_id == title_id,
                Interaction.event_type == "rating",
                Interaction.rating.is_not(None),
            )
        )
        avg_rating, rating_count = rating_stats.one()

        title = await self.db.get(Title, title_id)
        if title is None:
            return

        title.like_count = int(like_count or 0)
        title.rating_count = int(rating_count or 0)
        title.streamwise_avg_rating = float(avg_rating) if avg_rating is not None else None
