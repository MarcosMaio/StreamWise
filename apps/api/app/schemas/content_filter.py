import uuid

from pydantic import BaseModel, Field


class ContentFilterRequest(BaseModel):
    blocked_genre_ids: list[uuid.UUID] = Field(default_factory=list)
    max_certification: str | None = None


class ContentFilterResponse(BaseModel):
    blocked_genre_ids: list[uuid.UUID] = Field(default_factory=list)
    max_certification: str | None = None
