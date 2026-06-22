import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.routers import admin, auth, catalog, integrations, interactions, recommendations, titles, users
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


def configure_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.debug)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        payload = ErrorResponse(detail=str(exc.detail), code=str(exc.status_code))
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        payload = ErrorResponse(detail="Validation error", code="validation_error")
        return JSONResponse(
            status_code=422,
            content={**payload.model_dump(), "errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url.path)
        payload = ErrorResponse(detail="Internal server error", code="internal_error")
        return JSONResponse(status_code=500, content=payload.model_dump())

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(catalog.router)
    app.include_router(titles.router)
    app.include_router(interactions.router)
    app.include_router(recommendations.router)
    app.include_router(users.router)
    app.include_router(admin.router)
    app.include_router(integrations.router)

    return app


app = create_app()
