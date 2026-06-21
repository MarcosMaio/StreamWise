from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.interaction import InteractionRequest, InteractionResponse
from app.services.interaction_service import InteractionService

router = APIRouter(prefix="/titles", tags=["interactions"])


@router.post(
    "/{title_id}/interactions",
    response_model=InteractionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_interaction(
    title_id: UUID,
    data: InteractionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InteractionResponse:
    service = InteractionService(db)
    return await service.record_interaction(current_user.id, title_id, data)
