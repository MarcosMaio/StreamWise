from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class StreamingProviderBadge(BaseModel):
    id: UUID
    name: str
    logo_url: str | None = None
    availability_type: str = "flatrate"


class TitleSummary(BaseModel):
    id: UUID
    tmdb_id: int
    type: str
    title: str
    overview: str | None = None
    release_date: date | None = None
    poster_url: str | None = None
    streamwise_avg_rating: float | None = None
    like_count: int = 0
    genres: list[str] = Field(default_factory=list)
    streaming_providers: list[StreamingProviderBadge] = Field(default_factory=list)


class TitleListResponse(BaseModel):
    items: list[TitleSummary]
    total: int
    stale_data: bool = False
    availability_note: str | None = None


class TitleDetail(TitleSummary):
    tmdb_popularity: float = 0.0
    is_trending: bool = False
    certification: str | None = None
    availability_note: str | None = None
    rent_providers: list[StreamingProviderBadge] = Field(default_factory=list)
    buy_providers: list[StreamingProviderBadge] = Field(default_factory=list)
