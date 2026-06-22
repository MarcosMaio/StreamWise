import uuid
from datetime import datetime

from pydantic import BaseModel


class CatalogChangeItem(BaseModel):
    id: uuid.UUID
    title_id: uuid.UUID
    title_name: str
    provider_name: str
    change_type: str
    availability_type: str
    detected_at: datetime


class CatalogChangeListResponse(BaseModel):
    items: list[CatalogChangeItem]
    total: int
