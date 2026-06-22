from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.provider import StreamingProvider
from app.models.title import Genre
from app.models.user import User
from app.schemas.catalog import GenreListResponse, GenreOption, ProviderListResponse, ProviderOption
from app.schemas.catalog_changes import CatalogChangeItem, CatalogChangeListResponse
from app.schemas.title import TitleListResponse
from app.services.catalog_change_service import CatalogChangeService
from app.services.catalog_service import CatalogService
from app.services.parental_filter_service import ParentalFilterService
from app.services.vector_search_service import VectorSearchService

router = APIRouter(prefix="/catalog", tags=["catalog"])


async def _load_content_filter(db: AsyncSession, user: User):
    return await ParentalFilterService(db).load_for_user(user.id)


@router.get("/genres", response_model=GenreListResponse)
async def list_genres(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> GenreListResponse:
    result = await db.execute(select(Genre).order_by(Genre.name))
    genres = result.scalars().all()
    return GenreListResponse(items=[GenreOption(id=genre.id, name=genre.name) for genre in genres])


@router.get("/providers", response_model=ProviderListResponse)
async def list_providers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProviderListResponse:
    result = await db.execute(select(StreamingProvider).order_by(StreamingProvider.name))
    providers = result.scalars().all()
    return ProviderListResponse(
        items=[
            ProviderOption(
                id=provider.id,
                name=provider.name,
                logo_url=provider.logo_path,
            )
            for provider in providers
        ]
    )


@router.get("/trending", response_model=TitleListResponse)
async def get_trending(
    type: Literal["movie", "series", "all"] = Query(default="all"),
    limit: int = Query(default=20, ge=1, le=50),
    provider_ids: list[UUID] | None = Query(default=None),
    genre_ids: list[UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TitleListResponse:
    content_filter = await _load_content_filter(db, current_user)
    service = CatalogService(db)
    return await service.list_trending(
        title_type=type,
        limit=limit,
        provider_ids=provider_ids,
        genre_ids=genre_ids,
        content_filter=content_filter,
    )


@router.get("/new", response_model=TitleListResponse)
async def get_new_releases(
    limit: int = Query(default=20, ge=1, le=50),
    provider_ids: list[UUID] | None = Query(default=None),
    genre_ids: list[UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TitleListResponse:
    content_filter = await _load_content_filter(db, current_user)
    service = CatalogService(db)
    return await service.list_new_releases(
        limit=limit,
        provider_ids=provider_ids,
        genre_ids=genre_ids,
        content_filter=content_filter,
    )


@router.get("/search", response_model=TitleListResponse)
async def search_titles(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=50),
    provider_ids: list[UUID] | None = Query(default=None),
    genre_ids: list[UUID] | None = Query(default=None),
    type: Literal["movie", "series"] | None = Query(default=None),
    duration: Literal["short", "long"] | None = Query(default=None),
    mood: Literal["funny", "intense", "cozy", "thoughtful"] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TitleListResponse:
    service = VectorSearchService(db)
    return await service.search_by_query(
        q,
        limit=limit,
        provider_ids=provider_ids,
        genre_ids=genre_ids,
        title_type=type,
        duration=duration,
        mood=mood,
    )


@router.get("/changes", response_model=CatalogChangeListResponse)
async def get_catalog_changes(
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CatalogChangeListResponse:
    service = CatalogChangeService(db)
    rows = await service.list_recent_changes(limit=limit)
    items = [
        CatalogChangeItem(
            id=row.id,
            title_id=row.title_id,
            title_name=row.title_name,
            provider_name=row.provider_name,
            change_type=row.change_type,
            availability_type=row.availability_type,
            detected_at=row.detected_at,
        )
        for row in rows
    ]
    return CatalogChangeListResponse(items=items, total=len(items))
