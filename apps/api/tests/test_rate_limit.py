from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.middleware.rate_limit import RateLimitMiddleware


async def _ok(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _build_app(auth_limit: int = 2) -> Starlette:
    app = Starlette(routes=[Route("/auth/login", _ok, methods=["POST"])])
    app.add_middleware(
        RateLimitMiddleware,
        enabled=True,
        auth_limit_per_minute=auth_limit,
        search_limit_per_minute=5,
    )
    return app


def test_rate_limit_blocks_after_threshold():
    client = TestClient(_build_app(auth_limit=2))

    assert client.post("/auth/login").status_code == 200
    assert client.post("/auth/login").status_code == 200

    blocked = client.post("/auth/login")
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "429"


def test_rate_limit_skips_non_protected_paths():
    app = Starlette(routes=[Route("/health", _ok)])
    app.add_middleware(RateLimitMiddleware, enabled=True, auth_limit_per_minute=1)
    client = TestClient(app)

    for _ in range(5):
        assert client.get("/health").status_code == 200
