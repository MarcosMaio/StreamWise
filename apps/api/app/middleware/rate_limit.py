"""In-memory sliding-window rate limiting for sensitive endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

AUTH_PREFIX = "/auth/"
SEARCH_PATH = "/catalog/search"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        enabled: bool = True,
        auth_limit_per_minute: int = 10,
        search_limit_per_minute: int = 30,
        now_fn: Callable[[], float] | None = None,
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.auth_limit = auth_limit_per_minute
        self.search_limit = search_limit_per_minute
        self._now = now_fn or time.monotonic
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled or request.method == "OPTIONS":
            return await call_next(request)

        limit = self._limit_for_path(request.url.path)
        if limit is None:
            return await call_next(request)

        client_key = self._client_key(request)
        bucket_key = f"{client_key}:{request.url.path.split('?')[0]}"
        if self._is_limited(bucket_key, limit):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later.", "code": "429"},
            )

        return await call_next(request)

    def _limit_for_path(self, path: str) -> int | None:
        if path.startswith(AUTH_PREFIX):
            return self.auth_limit
        if path == SEARCH_PATH:
            return self.search_limit
        return None

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _is_limited(self, bucket_key: str, limit: int) -> bool:
        now = self._now()
        window = self._windows[bucket_key]
        cutoff = now - 60.0

        while window and window[0] <= cutoff:
            window.popleft()

        if len(window) >= limit:
            return True

        window.append(now)
        return False
