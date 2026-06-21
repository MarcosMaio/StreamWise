from pydantic import BaseModel, Field

from app.schemas.title import TitleSummary


class RecommendationItem(TitleSummary):
    score: float = 0.0
    reason_tags: list[str] = Field(default_factory=list)


class RecommendationListResponse(BaseModel):
    items: list[RecommendationItem]
    fallback_used: bool = False
