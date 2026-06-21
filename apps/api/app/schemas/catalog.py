from uuid import UUID

from pydantic import BaseModel, Field


class GenreOption(BaseModel):
    id: UUID
    name: str


class ProviderOption(BaseModel):
    id: UUID
    name: str
    logo_url: str | None = None


class GenreListResponse(BaseModel):
    items: list[GenreOption] = Field(default_factory=list)


class ProviderListResponse(BaseModel):
    items: list[ProviderOption] = Field(default_factory=list)
