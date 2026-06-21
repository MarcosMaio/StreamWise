import logging
from datetime import date, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.provider import StreamingProvider, TitleStreamingProvider
from app.models.title import Genre, Title, TitleGenre
from app.schemas.title import StreamingProviderBadge, TitleDetail, TitleListResponse, TitleSummary
from app.services.tmdb_client import TMDBClient, poster_url, provider_logo_url, tmdb_media_type

logger = logging.getLogger(__name__)

STALE_THRESHOLD = timedelta(hours=24)
COUNTRY_CODE = "BR"


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _title_name(item: dict[str, Any], media_type: str) -> str:
    if media_type == "series":
        return item.get("name") or item.get("title") or "Unknown"
    return item.get("title") or item.get("name") or "Unknown"


def _release_date(item: dict[str, Any], media_type: str) -> date | None:
    key = "first_air_date" if media_type == "series" else "release_date"
    return _parse_date(item.get(key))


class CatalogService:
    def __init__(self, session: AsyncSession, tmdb: TMDBClient | None = None) -> None:
        self._session = session
        self._tmdb = tmdb or TMDBClient()

    async def clear_catalog_flags(self) -> None:
        await self._session.execute(
            update(Title).values(is_trending=False, is_new_release=False)
        )

    async def upsert_title_from_tmdb(
        self,
        item: dict[str, Any],
        media_type: Literal["movie", "series"],
        *,
        is_trending: bool = False,
        is_new_release: bool = False,
    ) -> Title:
        tmdb_id = item["id"]
        result = await self._session.execute(select(Title).where(Title.tmdb_id == tmdb_id))
        title = result.scalar_one_or_none()
        now = datetime.utcnow()

        fields = {
            "type": media_type,
            "title": _title_name(item, media_type),
            "overview": item.get("overview"),
            "release_date": _release_date(item, media_type),
            "poster_path": item.get("poster_path"),
            "tmdb_popularity": float(item.get("popularity") or 0.0),
            "last_synced_at": now,
        }

        if title is None:
            title = Title(tmdb_id=tmdb_id, is_trending=is_trending, is_new_release=is_new_release, **fields)
            self._session.add(title)
        else:
            for key, value in fields.items():
                setattr(title, key, value)
            if is_trending:
                title.is_trending = True
            if is_new_release:
                title.is_new_release = True

        await self._session.flush()
        await self._sync_genres(title, item.get("genre_ids") or [])
        return title

    async def _sync_genres(self, title: Title, genre_ids: list[int]) -> None:
        await self._session.execute(delete(TitleGenre).where(TitleGenre.title_id == title.id))
        if not genre_ids:
            return

        result = await self._session.execute(
            select(Genre).where(Genre.tmdb_genre_id.in_(genre_ids))
        )
        genres = result.scalars().all()
        for genre in genres:
            self._session.add(TitleGenre(title_id=title.id, genre_id=genre.id))

    async def sync_watch_providers(self, title: Title) -> None:
        media = tmdb_media_type(title.type)
        try:
            data = await self._tmdb.get_watch_providers(media, title.tmdb_id)
        except Exception:
            logger.warning("Failed to fetch watch providers for tmdb_id=%s", title.tmdb_id)
            return

        br_data = (data.get("results") or {}).get(COUNTRY_CODE) or {}
        flatrate = br_data.get("flatrate") or []

        await self._session.execute(
            delete(TitleStreamingProvider).where(
                TitleStreamingProvider.title_id == title.id,
                TitleStreamingProvider.country_code == COUNTRY_CODE,
            )
        )

        for provider_data in flatrate:
            tmdb_provider_id = provider_data.get("provider_id")
            if tmdb_provider_id is None:
                continue

            result = await self._session.execute(
                select(StreamingProvider).where(
                    StreamingProvider.tmdb_provider_id == tmdb_provider_id
                )
            )
            provider = result.scalar_one_or_none()
            if provider is None:
                provider = StreamingProvider(
                    tmdb_provider_id=tmdb_provider_id,
                    name=provider_data.get("provider_name") or f"Provider {tmdb_provider_id}",
                    logo_path=provider_data.get("logo_path"),
                )
                self._session.add(provider)
                await self._session.flush()

            self._session.add(
                TitleStreamingProvider(
                    title_id=title.id,
                    provider_id=provider.id,
                    country_code=COUNTRY_CODE,
                    availability_type="flatrate",
                )
            )

    async def get_stale_data_info(self) -> tuple[bool, str | None]:
        result = await self._session.execute(select(func.max(Title.last_synced_at)))
        latest_sync = result.scalar_one_or_none()
        if latest_sync is None:
            return True, "Catalog has not been synced yet. Streaming availability may be unavailable."

        if latest_sync.tzinfo is not None:
            latest_sync = latest_sync.replace(tzinfo=None)

        if datetime.utcnow() - latest_sync > STALE_THRESHOLD:
            return True, "Catalog data is older than 24 hours. Streaming availability may be outdated."

        return False, None

    def _apply_provider_filter(self, query, provider_ids: list[UUID] | None):
        if not provider_ids:
            return query
        return query.join(
            TitleStreamingProvider,
            TitleStreamingProvider.title_id == Title.id,
        ).where(
            TitleStreamingProvider.provider_id.in_(provider_ids),
            TitleStreamingProvider.country_code == COUNTRY_CODE,
            TitleStreamingProvider.availability_type == "flatrate",
        )

    def _apply_genre_filter(self, query, genre_ids: list[UUID] | None):
        if not genre_ids:
            return query
        return query.join(TitleGenre, TitleGenre.title_id == Title.id).where(
            TitleGenre.genre_id.in_(genre_ids)
        )

    async def list_trending(
        self,
        *,
        title_type: Literal["movie", "series", "all"] = "all",
        limit: int = 20,
        provider_ids: list[UUID] | None = None,
        genre_ids: list[UUID] | None = None,
    ) -> TitleListResponse:
        query = (
            select(Title)
            .where(Title.is_trending.is_(True))
            .options(
                selectinload(Title.title_genres).selectinload(TitleGenre.genre),
                selectinload(Title.streaming_providers).selectinload(
                    TitleStreamingProvider.provider
                ),
            )
            .order_by(Title.tmdb_popularity.desc())
            .limit(min(limit, 50))
        )
        if title_type != "all":
            query = query.where(Title.type == title_type)
        query = self._apply_genre_filter(query, genre_ids)
        query = self._apply_provider_filter(query, provider_ids)

        result = await self._session.execute(query)
        titles = result.scalars().unique().all()
        stale, note = await self.get_stale_data_info()
        items = [self._to_summary(title) for title in titles]
        return TitleListResponse(items=items, total=len(items), stale_data=stale, availability_note=note)

    async def list_new_releases(
        self,
        *,
        limit: int = 20,
        provider_ids: list[UUID] | None = None,
        genre_ids: list[UUID] | None = None,
    ) -> TitleListResponse:
        query = (
            select(Title)
            .where(Title.is_new_release.is_(True))
            .options(
                selectinload(Title.title_genres).selectinload(TitleGenre.genre),
                selectinload(Title.streaming_providers).selectinload(
                    TitleStreamingProvider.provider
                ),
            )
            .order_by(Title.release_date.desc().nullslast(), Title.tmdb_popularity.desc())
            .limit(min(limit, 50))
        )
        query = self._apply_genre_filter(query, genre_ids)
        query = self._apply_provider_filter(query, provider_ids)

        result = await self._session.execute(query)
        titles = result.scalars().unique().all()
        stale, note = await self.get_stale_data_info()
        items = [self._to_summary(title) for title in titles]
        return TitleListResponse(items=items, total=len(items), stale_data=stale, availability_note=note)

    async def get_title(self, title_id: UUID) -> TitleDetail | None:
        result = await self._session.execute(
            select(Title)
            .where(Title.id == title_id)
            .options(
                selectinload(Title.title_genres).selectinload(TitleGenre.genre),
                selectinload(Title.streaming_providers).selectinload(
                    TitleStreamingProvider.provider
                ),
            )
        )
        title = result.scalar_one_or_none()
        if title is None:
            return None

        summary = self._to_summary(title)
        _, note = await self.get_stale_data_info()
        return TitleDetail(
            **summary.model_dump(),
            tmdb_popularity=title.tmdb_popularity,
            is_trending=title.is_trending,
            availability_note=note,
        )

    def _to_summary(self, title: Title) -> TitleSummary:
        genres = [tg.genre.name for tg in title.title_genres if tg.genre]
        providers = [
            StreamingProviderBadge(
                id=link.provider.id,
                name=link.provider.name,
                logo_url=provider_logo_url(link.provider.logo_path),
                availability_type=link.availability_type,
            )
            for link in title.streaming_providers
            if link.country_code == COUNTRY_CODE and link.provider
        ]
        return TitleSummary(
            id=title.id,
            tmdb_id=title.tmdb_id,
            type=title.type,
            title=title.title,
            overview=title.overview,
            release_date=title.release_date,
            poster_url=poster_url(title.poster_path),
            streamwise_avg_rating=title.streamwise_avg_rating,
            like_count=title.like_count,
            genres=genres,
            streaming_providers=providers,
        )
