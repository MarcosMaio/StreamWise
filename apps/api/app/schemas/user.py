import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserProfile(BaseModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str
    country_code: str = "BR"
    onboarding_complete: bool = False
    genre_ids: list[uuid.UUID] = Field(default_factory=list)
    streaming_provider_ids: list[uuid.UUID] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PreferencesRequest(BaseModel):
    genre_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    streaming_provider_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    seed_like_title_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)

    @field_validator("genre_ids")
    @classmethod
    def validate_genre_ids(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if not value:
            raise ValueError("At least one genre is required")
        return value

    @field_validator("streaming_provider_ids")
    @classmethod
    def validate_streaming_provider_ids(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if not value:
            raise ValueError("At least one streaming provider is required")
        return value
