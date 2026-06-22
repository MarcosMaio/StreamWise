from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.title import StreamingProviderBadge, TitleSummary


TimeBudget = Literal["short", "medium", "long"]
Mood = Literal["funny", "intense", "cozy", "thoughtful"]
Company = Literal["solo", "date", "family"]


class SessionContext(BaseModel):
    time_budget: TimeBudget | None = None
    mood: Mood | None = None
    company: Company | None = None


class SeriesProgressRequest(BaseModel):
    season: int = Field(ge=1)
    episode: int = Field(ge=1)


class SeriesProgressResponse(BaseModel):
    title_id: str
    season: int
    episode: int


class ContinueWatchingItem(TitleSummary):
    season: int
    episode: int


class ContinueWatchingResponse(BaseModel):
    items: list[ContinueWatchingItem]
    total: int
