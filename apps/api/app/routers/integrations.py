from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/trakt/authorize")
async def trakt_authorize(settings: Settings = Depends(get_settings)) -> dict:
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
        }
    )
    return {"authorize_url": f"https://trakt.tv/oauth/authorize?{params}"}


@router.get("/trakt/callback")
async def trakt_callback(
    code: str | None = None,
    settings: Settings = Depends(get_settings),
) -> dict:
    if not settings.trakt_client_id or not settings.trakt_client_secret.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trakt integration is not configured",
        )
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing OAuth code")

    return {
        "status": "stub",
        "message": "Trakt token exchange is not implemented in MVP; configure import via CSV instead.",
        "code_received": True,
    }
