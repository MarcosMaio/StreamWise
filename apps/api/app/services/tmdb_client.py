import logging
from typing import Any, Literal

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

MediaType = Literal["movie", "tv"]
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


class TMDBClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._api_key = self._settings.tmdb_api_key

    def _params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        params = {"api_key": self._api_key, "language": "pt-BR"}
        if extra:
            params.update(extra)
        return params

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._api_key:
            raise RuntimeError("TMDB_API_KEY is not configured")

        url = f"{TMDB_BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=self._params(params))
            response.raise_for_status()
            return response.json()

    async def get_trending(self, media_type: MediaType, page: int = 1) -> dict[str, Any]:
        return await self._get(f"/trending/{media_type}/day", {"page": page})

    async def get_now_playing(self, page: int = 1) -> dict[str, Any]:
        return await self._get("/movie/now_playing", {"page": page})

    async def get_on_the_air(self, page: int = 1) -> dict[str, Any]:
        return await self._get("/tv/on_the_air", {"page": page})

    async def get_details(self, media_type: MediaType, tmdb_id: int) -> dict[str, Any]:
        return await self._get(f"/{media_type}/{tmdb_id}")

    async def get_watch_providers(self, media_type: MediaType, tmdb_id: int) -> dict[str, Any]:
        return await self._get(f"/{media_type}/{tmdb_id}/watch/providers")


def poster_url(poster_path: str | None) -> str | None:
    if not poster_path:
        return None
    return f"{TMDB_IMAGE_BASE}{poster_path}"


def provider_logo_url(logo_path: str | None) -> str | None:
    if not logo_path:
        return None
    return f"{TMDB_IMAGE_BASE}{logo_path}"


def tmdb_media_type(title_type: str) -> MediaType:
    return "tv" if title_type == "series" else "movie"
