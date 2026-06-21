from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.provider import StreamingProvider
from app.models.title import Genre
from app.models.user import User
from app.schemas.catalog import GenreListResponse, GenreOption, ProviderListResponse, ProviderOption
from app.schemas.title import TitleListResponse
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/catalog", tags=["catalog"])


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
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TitleListResponse:
    service = CatalogService(db)
    return await service.list_trending(title_type=type, limit=limit)


@router.get("/new", response_model=TitleListResponse)
async def get_new_releases(
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TitleListResponse:
    service = CatalogService(db)
    return await service.list_new_releases(limit=limit)
