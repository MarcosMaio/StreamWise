import uuid

from pydantic import BaseModel, Field


class StreamingAffinity(BaseModel):
    provider_id: uuid.UUID
    provider_name: str
    score: float


class StreamingAffinityResponse(BaseModel):
    providers: list[StreamingAffinity] = Field(default_factory=list)
