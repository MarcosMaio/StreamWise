import uuid

from pydantic import BaseModel, Field


class ContentFilterRequest(BaseModel):
    blocked_genre_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    max_certification: str | None = Field(default=None, max_length=16)


class ContentFilterResponse(BaseModel):
    blocked_genre_ids: list[uuid.UUID] = Field(default_factory=list)
    max_certification: str | None = None
