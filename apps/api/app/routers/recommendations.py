from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.context import SessionContext
from app.schemas.recommendation import RecommendationListResponse
from app.services.recommendation_service import RecommendationService
from app.services.bandit_service import BanditService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/for-you", response_model=RecommendationListResponse)
async def get_for_you_feed(
    limit: int = Query(default=20, ge=1, le=50),
    provider_ids: list[UUID] | None = Query(default=None),
    time_budget: Literal["short", "medium", "long"] | None = Query(default=None),
    mood: Literal["funny", "intense", "cozy", "thoughtful"] | None = Query(default=None),
    company: Literal["solo", "date", "family"] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecommendationListResponse:
    context = SessionContext(time_budget=time_budget, mood=mood, company=company)
    service = RecommendationService(db)
    return await service.get_for_you(
        current_user,
        limit=limit,
        provider_ids=provider_ids,
        context=context if any((time_budget, mood, company)) else None,
    )


@router.post("/bandit/click")
async def log_bandit_click(
    title_id: UUID = Query(...),
    exploration: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = BanditService(db)
    await service.log_click(current_user.id, title_id, is_exploration=exploration)
    return {"status": "logged"}
