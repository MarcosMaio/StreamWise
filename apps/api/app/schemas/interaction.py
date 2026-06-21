from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.title import TitleSummary

EventType = Literal["like", "dislike", "rating", "watchlist", "watched"]


class InteractionRequest(BaseModel):
    event_type: EventType
    rating: float | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="after")
    def validate_rating_for_event(self) -> "InteractionRequest":
        if self.event_type == "rating" and self.rating is None:
            raise ValueError("rating is required when event_type is rating")
        if self.event_type != "rating" and self.rating is not None:
            raise ValueError("rating is only allowed when event_type is rating")
        return self


class InteractionResponse(BaseModel):
    id: UUID
    event_type: EventType
    title: TitleSummary
