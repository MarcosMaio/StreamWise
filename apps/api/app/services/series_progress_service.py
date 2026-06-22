from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interaction import UserSeriesProgress
from app.models.provider import TitleStreamingProvider
from app.models.title import Title, TitleGenre
from app.schemas.context import ContinueWatchingItem, ContinueWatchingResponse, SeriesProgressResponse
from app.services.catalog_service import CatalogService


class SeriesProgressService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.catalog = CatalogService(db)

    async def upsert_progress(
        self,
        user_id: UUID,
        title_id: UUID,
        *,
        season: int,
        episode: int,
    ) -> SeriesProgressResponse:
        title = await self.db.get(Title, title_id)
        if title is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Title not found")
        if title.type != "series":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Progress tracking is only supported for series",
            )

        progress = await self.db.get(UserSeriesProgress, (user_id, title_id))
        now = datetime.now(UTC).replace(tzinfo=None)
        if progress is None:
            progress = UserSeriesProgress(
                user_id=user_id,
                title_id=title_id,
                season=season,
                episode=episode,
                updated_at=now,
            )
            self.db.add(progress)
        else:
            progress.season = season
            progress.episode = episode
            progress.updated_at = now

        await self.db.commit()
        return SeriesProgressResponse(
            title_id=str(title_id),
            season=season,
            episode=episode,
        )

    async def list_continue_watching(
        self, user_id: UUID, *, limit: int = 20
    ) -> ContinueWatchingResponse:
        result = await self.db.execute(
            select(UserSeriesProgress)
            .where(UserSeriesProgress.user_id == user_id)
            .options(
                selectinload(UserSeriesProgress.title)
                .selectinload(Title.title_genres)
                .selectinload(TitleGenre.genre),
                selectinload(UserSeriesProgress.title)
                .selectinload(Title.streaming_providers)
                .selectinload(TitleStreamingProvider.provider),
            )
            .order_by(UserSeriesProgress.updated_at.desc())
            .limit(min(limit, 50))
        )
        rows = result.scalars().unique().all()
        items: list[ContinueWatchingItem] = []
        for row in rows:
            if row.title is None:
                continue
            summary = self.catalog._to_summary(row.title)
            items.append(
                ContinueWatchingItem(
                    **summary.model_dump(),
                    season=row.season,
                    episode=row.episode,
                )
            )

        return ContinueWatchingResponse(items=items, total=len(items))
