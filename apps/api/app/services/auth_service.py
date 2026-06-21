import uuid

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.core.jwt import create_access_token, create_refresh_token
from app.core.security import hash_password, verify_password
from app.models.user import OAuthAccount, User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.schemas.user import UserProfile


class AuthService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def register(self, data: RegisterRequest) -> AuthResponse:
        existing = await self.db.scalar(select(User).where(User.email == data.email))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            display_name=data.display_name,
        )
        self.db.add(user)
        await self.db.commit()
        user = await self._load_user(user.id)
        return self._build_auth_response(user)

    async def login(self, data: LoginRequest) -> AuthResponse:
        user = await self.db.scalar(select(User).where(User.email == data.email))
        if user is None or user.password_hash is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        if not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        user = await self._load_user(user.id)
        return self._build_auth_response(user)

    async def google_oauth(self, id_token: str) -> AuthResponse:
        if not self.settings.google_client_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth is not configured",
            )

        google_user = await self._verify_google_id_token(id_token)
        email = google_user.get("email")
        google_sub = google_user.get("sub")
        if not email or not google_sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token",
            )

        oauth_account = await self.db.scalar(
            select(OAuthAccount).where(
                OAuthAccount.provider == "google",
                OAuthAccount.provider_account_id == google_sub,
            )
        )
        if oauth_account:
            user = await self._load_user(oauth_account.user_id)
            return self._build_auth_response(user)

        user = await self.db.scalar(select(User).where(User.email == email))
        if user is None:
            display_name = google_user.get("name") or email.split("@")[0]
            user = User(email=email, display_name=display_name, password_hash=None)
            self.db.add(user)
            await self.db.flush()
        else:
            existing_oauth = await self.db.scalar(
                select(OAuthAccount).where(
                    OAuthAccount.user_id == user.id,
                    OAuthAccount.provider == "google",
                )
            )
            if existing_oauth is None:
                self.db.add(
                    OAuthAccount(
                        user_id=user.id,
                        provider="google",
                        provider_account_id=google_sub,
                    )
                )
                await self.db.commit()
            user = await self._load_user(user.id)
            return self._build_auth_response(user)

        self.db.add(
            OAuthAccount(
                user_id=user.id,
                provider="google",
                provider_account_id=google_sub,
            )
        )
        await self.db.commit()
        user = await self._load_user(user.id)
        return self._build_auth_response(user)

    async def _load_user(self, user_id: uuid.UUID) -> User:
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.preferences),
                selectinload(User.streaming_affinities),
            )
        )
        return result.scalar_one()

    async def _verify_google_id_token(self, id_token: str) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token},
            )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token",
            )

        payload = response.json()
        if payload.get("aud") != self.settings.google_client_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token audience",
            )
        return payload

    def _build_auth_response(self, user: User) -> AuthResponse:
        return AuthResponse(
            access_token=create_access_token(user.id, self.settings),
            refresh_token=create_refresh_token(user.id, self.settings),
            user=user_to_profile(user),
        )


def user_to_profile(user: User) -> UserProfile:
    genre_ids = [pref.genre_id for pref in user.preferences]
    streaming_provider_ids = [affinity.provider_id for affinity in user.streaming_affinities]
    return UserProfile(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        country_code=user.country_code,
        onboarding_complete=user.onboarding_complete,
        genre_ids=genre_ids,
        streaming_provider_ids=streaming_provider_ids,
    )
