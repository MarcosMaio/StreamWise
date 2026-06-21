from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import PreferencesRequest, UserProfile
from app.services.auth_service import user_to_profile
from app.services.user_preference_service import UserPreferenceService

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
