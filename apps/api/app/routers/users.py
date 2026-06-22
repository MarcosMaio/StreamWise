from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.affinity import StreamingAffinityResponse
from app.schemas.context import ContinueWatchingResponse
from app.schemas.title import TitleListResponse
from app.schemas.user import PreferencesRequest, UserProfile
from app.services.affinity_service import AffinityService
from app.services.auth_service import user_to_profile
from app.services.series_progress_service import SeriesProgressService
from app.services.user_preference_service import UserPreferenceService
from app.services.user_profile_service import UserProfileService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)) -> UserProfile:
    return user_to_profile(current_user)


@router.put("/me/preferences", response_model=UserProfile)
async def update_preferences(
    data: PreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    service = UserPreferenceService(db)
    user = await service.save_preferences(current_user, data)
    return user_to_profile(user)


@router.get("/me/likes", response_model=TitleListResponse)
async def get_likes(
    limit: int = Query(default=50, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TitleListResponse:
    service = UserProfileService(db)
    return await service.list_titles_by_event(current_user.id, "like", limit=limit)


@router.get("/me/watchlist", response_model=TitleListResponse)
async def get_watchlist(
    limit: int = Query(default=50, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TitleListResponse:
    service = UserProfileService(db)
    return await service.list_titles_by_event(current_user.id, "watchlist", limit=limit)


@router.get("/me/affinity", response_model=StreamingAffinityResponse)
async def get_affinity(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingAffinityResponse:
    service = AffinityService(db)
    providers = await service.list_for_user(current_user.id)
    return StreamingAffinityResponse(providers=providers)


@router.get("/me/continue-watching", response_model=ContinueWatchingResponse)
async def get_continue_watching(
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContinueWatchingResponse:
    service = SeriesProgressService(db)
    return await service.list_continue_watching(current_user.id, limit=limit)
