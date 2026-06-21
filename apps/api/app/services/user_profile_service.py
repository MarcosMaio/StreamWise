from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interaction import Interaction
from app.models.provider import TitleStreamingProvider
from app.models.title import Title, TitleGenre
from app.schemas.title import TitleListResponse
from app.services.catalog_service import CatalogService


class UserProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.catalog = CatalogService(db)

    async def list_titles_by_event(
        self,
        user_id: UUID,
        event_type: str,
        *,
        limit: int = 50,
    ) -> TitleListResponse:
        result = await self.db.execute(
            select(Interaction)
            .where(
                Interaction.user_id == user_id,
                Interaction.event_type == event_type,
            )
            .options(
                selectinload(Interaction.title)
                .selectinload(Title.title_genres)
                .selectinload(TitleGenre.genre),
                selectinload(Interaction.title)
                .selectinload(Title.streaming_providers)
                .selectinload(TitleStreamingProvider.provider),
            )
            .order_by(Interaction.created_at.desc())
            .limit(min(limit, 50))
        )
        interactions = result.scalars().unique().all()
        items = [
            self.catalog._to_summary(interaction.title)
            for interaction in interactions
            if interaction.title is not None
        ]
        return TitleListResponse(items=items, total=len(items))
