from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.p2 import UserContentFilter
from app.models.title import Title, TitleGenre
from app.schemas.user import ContentFilterRequest, ContentFilterResponse


CERT_RANK = {"L": 0, "10": 1, "12": 2, "14": 3, "16": 4, "18": 5}


class ParentalFilterService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_filter(self, user_id: UUID) -> UserContentFilter | None:
        return await self.db.get(UserContentFilter, user_id)

    async def upsert_filter(
        self, user_id: UUID, data: ContentFilterRequest
    ) -> ContentFilterResponse:
        record = await self.db.get(UserContentFilter, user_id)
        if record is None:
            record = UserContentFilter(user_id=user_id)
            self.db.add(record)

        record.blocked_genre_ids = [str(item) for item in data.blocked_genre_ids]
        record.max_certification = data.max_certification
        await self.db.commit()
        return ContentFilterResponse(
            blocked_genre_ids=data.blocked_genre_ids,
            max_certification=data.max_certification,
        )

    @staticmethod
    def allows_title(title: Title, content_filter: UserContentFilter | None) -> bool:
        if content_filter is None:
            return True

        blocked = {UUID(str(item)) for item in (content_filter.blocked_genre_ids or [])}
        if blocked:
            title_genre_ids = {tg.genre_id for tg in title.title_genres}
            if title_genre_ids.intersection(blocked):
                return False

        if content_filter.max_certification and title.certification:
            max_rank = CERT_RANK.get(content_filter.max_certification.upper(), 99)
            title_rank = CERT_RANK.get(title.certification.upper(), 99)
            if title_rank > max_rank:
                return False

        return True

    @staticmethod
    def apply_to_titles(
        titles: list[Title], content_filter: UserContentFilter | None
    ) -> list[Title]:
        if content_filter is None:
            return titles
        return [title for title in titles if ParentalFilterService.allows_title(title, content_filter)]

    async def load_for_user(self, user_id: UUID) -> UserContentFilter | None:
        result = await self.db.execute(
            select(UserContentFilter).where(UserContentFilter.user_id == user_id)
        )
        return result.scalar_one_or_none()
