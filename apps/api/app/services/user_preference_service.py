import uuid

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.embedding import UserStreamingAffinity
from app.models.interaction import Interaction, UserPreference
from app.models.provider import StreamingProvider
from app.models.title import Genre, Title
from app.models.user import User
from app.schemas.user import PreferencesRequest


class UserPreferenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def save_preferences(self, user: User, data: PreferencesRequest) -> User:
        await self._validate_genre_ids(data.genre_ids)
        await self._validate_provider_ids(data.streaming_provider_ids)
        if data.seed_like_title_ids:
            await self._validate_title_ids(data.seed_like_title_ids)

        await self.db.execute(
            delete(UserPreference).where(
                UserPreference.user_id == user.id,
                UserPreference.source == "onboarding",
            )
        )

        for genre_id in data.genre_ids:
            self.db.add(
                UserPreference(
                    user_id=user.id,
                    genre_id=genre_id,
                    source="onboarding",
                )
            )

        await self.db.execute(
            delete(UserStreamingAffinity).where(UserStreamingAffinity.user_id == user.id)
        )

        provider_count = len(data.streaming_provider_ids)
        uniform_score = 1.0 / provider_count
        for provider_id in data.streaming_provider_ids:
            self.db.add(
                UserStreamingAffinity(
                    user_id=user.id,
                    provider_id=provider_id,
                    score=uniform_score,
                )
            )

        if data.seed_like_title_ids:
            await self._seed_likes(user.id, data.seed_like_title_ids)

        user.onboarding_complete = True
        await self.db.commit()
        user = await self._load_user(user.id)
        pref_result = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user.id)
        )
        user.preferences = list(pref_result.scalars().all())
        aff_result = await self.db.execute(
            select(UserStreamingAffinity).where(UserStreamingAffinity.user_id == user.id)
        )
        user.streaming_affinities = list(aff_result.scalars().all())
        return user

    async def _validate_genre_ids(self, genre_ids: list[uuid.UUID]) -> None:
        result = await self.db.execute(select(Genre.id).where(Genre.id.in_(genre_ids)))
        found = set(result.scalars().all())
        missing = set(genre_ids) - found
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown genre ids: {sorted(str(item) for item in missing)}",
            )

    async def _validate_provider_ids(self, provider_ids: list[uuid.UUID]) -> None:
        result = await self.db.execute(
            select(StreamingProvider.id).where(StreamingProvider.id.in_(provider_ids))
        )
        found = set(result.scalars().all())
        missing = set(provider_ids) - found
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown streaming provider ids: {sorted(str(item) for item in missing)}",
            )

    async def _validate_title_ids(self, title_ids: list[uuid.UUID]) -> None:
        result = await self.db.execute(select(Title.id).where(Title.id.in_(title_ids)))
        found = set(result.scalars().all())
        missing = set(title_ids) - found
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown title ids: {sorted(str(item) for item in missing)}",
            )

    async def _seed_likes(self, user_id: uuid.UUID, title_ids: list[uuid.UUID]) -> None:
        result = await self.db.execute(
            select(Interaction.title_id).where(
                Interaction.user_id == user_id,
                Interaction.event_type == "like",
                Interaction.title_id.in_(title_ids),
            )
        )
        existing = set(result.scalars().all())

        for title_id in title_ids:
            if title_id in existing:
                continue
            self.db.add(
                Interaction(
                    user_id=user_id,
                    title_id=title_id,
                    event_type="like",
                )
            )

    async def _load_user(self, user_id: uuid.UUID) -> User:
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.preferences),
                selectinload(User.streaming_affinities),
            )
        )
        return result.scalar_one()
