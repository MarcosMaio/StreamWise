from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_db
from app.models.embedding import ModelVersion

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(
    x_admin_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API is not configured",
        )
    if x_admin_token != settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.get("/metrics/recommendations")
async def get_recommendation_metrics(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(ModelVersion)
        .where(ModelVersion.is_active.is_(True))
        .order_by(ModelVersion.trained_at.desc())
        .limit(1)
    )
    model = result.scalar_one_or_none()
    if model is None:
        return {"model_version": None, "metrics": None}

    return {
        "model_version": model.version,
        "trained_at": model.trained_at.isoformat(),
        "metrics": model.metrics,
    }
