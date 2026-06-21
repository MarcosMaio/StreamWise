from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.recommendation import RecommendationListResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/for-you", response_model=RecommendationListResponse)
async def get_for_you_feed(
    limit: int = Query(default=20, ge=1, le=50),
    provider_ids: list[UUID] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecommendationListResponse:
    service = RecommendationService(db)
    return await service.get_for_you(current_user, limit=limit, provider_ids=provider_ids)
