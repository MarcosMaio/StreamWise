from uuid import UUID
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.import_service import ImportService

router = APIRouter(prefix="/integrations", tags=["integrations"])

_TRAKT_TOKEN_URL = "https://api.trakt.tv/oauth/token"
_TRAKT_WATCHLIST_MOVIES_URL = "https://api.trakt.tv/users/me/watchlist/movies"
_TRAKT_WATCHLIST_SHOWS_URL = "https://api.trakt.tv/users/me/watchlist/shows"


@router.get("/trakt/authorize")
async def trakt_authorize(
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    if not settings.trakt_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trakt integration is not configured",
        )

    params = urlencode(
        {
            "response_type": "code",
            "client_id": settings.trakt_client_id,
            "redirect_uri": settings.trakt_redirect_uri,
            "state": str(current_user.id),
        }
    )
    return {"authorize_url": f"https://trakt.tv/oauth/authorize?{params}"}


@router.get("/trakt/callback")
async def trakt_callback(
    code: str | None = None,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    if not settings.trakt_client_id or not settings.trakt_client_secret.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trakt integration is not configured",
        )
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing OAuth code")
    if not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing state (user identity)")

    try:
        user_id = UUID(state)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter")

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_response = await client.post(
            _TRAKT_TOKEN_URL,
            json={
                "code": code,
                "client_id": settings.trakt_client_id,
                "client_secret": settings.trakt_client_secret.get_secret_value(),
                "redirect_uri": settings.trakt_redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Trakt token exchange failed: {token_response.status_code}",
        )

    access_token = token_response.json().get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="No access_token in Trakt response")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "trakt-api-version": "2",
        "trakt-api-key": settings.trakt_client_id,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        movies_resp, shows_resp = await _fetch_watchlist(client, headers)

    tmdb_ids = _extract_tmdb_ids(movies_resp, "movie") + _extract_tmdb_ids(shows_resp, "show")

    if not tmdb_ids:
        return {"imported": 0, "skipped": 0, "missing_tmdb_ids": []}

    csv_content = "tmdb_id\n" + "\n".join(str(tid) for tid in tmdb_ids)
    service = ImportService(db)
    result = await service.import_watchlist_csv(user_id, csv_content)
    return result


async def _fetch_watchlist(client: httpx.AsyncClient, headers: dict) -> tuple[list, list]:
    movies_resp = await client.get(_TRAKT_WATCHLIST_MOVIES_URL, headers=headers)
    shows_resp = await client.get(_TRAKT_WATCHLIST_SHOWS_URL, headers=headers)
    movies = movies_resp.json() if movies_resp.status_code == 200 else []
    shows = shows_resp.json() if shows_resp.status_code == 200 else []
    return movies, shows


def _extract_tmdb_ids(items: list, media_type: str) -> list[int]:
    result = []
    for item in items:
        media = item.get(media_type, {})
        tmdb_id = (media.get("ids") or {}).get("tmdb")
        if tmdb_id:
            result.append(int(tmdb_id))
    return result
