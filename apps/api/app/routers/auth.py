from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.auth import AuthResponse, GoogleOAuthRequest, LoginRequest, RegisterRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(db, settings)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    return await auth_service.register(data)


@router.post("/login", response_model=AuthResponse)
async def login(
    data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    return await auth_service.login(data)


@router.post("/oauth/google", response_model=AuthResponse)
async def google_oauth(
    data: GoogleOAuthRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    return await auth_service.google_oauth(data.id_token)
