from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.title import TitleDetail, TitleListResponse
from app.services.catalog_service import CatalogService
from app.services.vector_search_service import VectorSearchService

router = APIRouter(prefix="/titles", tags=["titles"])


@router.get("/{title_id}/similar", response_model=TitleListResponse)
async def get_similar_titles(
    title_id: UUID,
    limit: int = Query(default=20, ge=1, le=50),
    provider_ids: list[UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TitleListResponse:
    catalog = CatalogService(db)
    if await catalog.get_title(title_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Title not found")

    service = VectorSearchService(db)
    return await service.find_similar_titles(title_id, limit=limit, provider_ids=provider_ids)


@router.get("/{title_id}", response_model=TitleDetail)
async def get_title(
    title_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TitleDetail:
    service = CatalogService(db)
    detail = await service.get_title(title_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Title not found")
    return detail
