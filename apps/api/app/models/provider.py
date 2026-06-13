import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.embedding import UserStreamingAffinity
    from app.models.title import Title


class StreamingProvider(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "streaming_providers"

    tmdb_provider_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    logo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    title_links: Mapped[list["TitleStreamingProvider"]] = relationship(back_populates="provider")
    user_affinities: Mapped[list["UserStreamingAffinity"]] = relationship(back_populates="provider")


class TitleStreamingProvider(Base):
    __tablename__ = "title_streaming_providers"

    title_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("titles.id", ondelete="CASCADE"), primary_key=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("streaming_providers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    country_code: Mapped[str] = mapped_column(String(2), primary_key=True, default="BR")
    availability_type: Mapped[str] = mapped_column(String(20), primary_key=True)

    title: Mapped["Title"] = relationship(back_populates="streaming_providers")
    provider: Mapped["StreamingProvider"] = relationship(back_populates="title_links")
