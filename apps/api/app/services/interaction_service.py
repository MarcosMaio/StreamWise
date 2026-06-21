from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import Interaction
from app.models.title import Title
from app.schemas.interaction import InteractionRequest, InteractionResponse
from app.services.affinity_service import AffinityService
from app.services.catalog_service import CatalogService
from app.services.title_aggregate_service import TitleAggregateService


class InteractionService:
    OPPOSING_EVENTS = {
        "like": "dislike",
        "dislike": "like",
    }
    AGGREGATE_EVENTS = {"like", "rating"}

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.aggregates = TitleAggregateService(db)
        self.affinity = AffinityService(db)
        self.catalog = CatalogService(db)

    async def record_interaction(
        self,
        user_id: UUID,
        title_id: UUID,
        data: InteractionRequest,
    ) -> InteractionResponse:
        await self._get_title(title_id)
        opposing = self.OPPOSING_EVENTS.get(data.event_type)
        if opposing:
            await self._remove_interaction(user_id, title_id, opposing)

        interaction = await self._upsert_interaction(user_id, title_id, data)

        if data.event_type in self.AGGREGATE_EVENTS:
            await self.aggregates.refresh_title_aggregates(title_id)

        if data.event_type in {"like", "dislike"}:
            await self.affinity.recompute_for_user(user_id)

        await self.db.commit()

        detail = await self.catalog.get_title(title_id)
        if detail is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Title not found",
            )

        return InteractionResponse(
            id=interaction.id,
            event_type=data.event_type,
            title=detail,
        )

    async def _get_title(self, title_id: UUID) -> Title:
        title = await self.db.get(Title, title_id)
        if title is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Title not found",
            )
        return title

    async def _upsert_interaction(
        self,
        user_id: UUID,
        title_id: UUID,
        data: InteractionRequest,
    ) -> Interaction:
        result = await self.db.execute(
            select(Interaction).where(
                Interaction.user_id == user_id,
                Interaction.title_id == title_id,
                Interaction.event_type == data.event_type,
            )
        )
        interaction = result.scalar_one_or_none()

        if interaction is None:
            interaction = Interaction(
                user_id=user_id,
                title_id=title_id,
                event_type=data.event_type,
                rating=data.rating,
            )
            self.db.add(interaction)
        else:
            interaction.rating = data.rating

        await self.db.flush()
        return interaction

    async def _remove_interaction(self, user_id: UUID, title_id: UUID, event_type: str) -> None:
        result = await self.db.execute(
            select(Interaction).where(
                Interaction.user_id == user_id,
                Interaction.title_id == title_id,
                Interaction.event_type == event_type,
            )
        )
        interaction = result.scalar_one_or_none()
        if interaction is None:
            return

        await self.db.delete(interaction)
        await self.db.flush()

        if event_type in self.AGGREGATE_EVENTS:
            await self.aggregates.refresh_title_aggregates(title_id)
