import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.embedding import TitleEmbedding
    from app.models.interaction import Interaction
    from app.models.provider import TitleStreamingProvider


class Genre(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "genres"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    tmdb_genre_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)

    title_genres: Mapped[list["TitleGenre"]] = relationship(back_populates="genre")


class Title(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "titles"

    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    movielens_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tmdb_popularity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    streamwise_avg_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_trending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_new_release: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(nullable=True)

    certification: Mapped[str | None] = mapped_column(String(10), nullable=True)

    title_genres: Mapped[list["TitleGenre"]] = relationship(back_populates="title")
    streaming_providers: Mapped[list["TitleStreamingProvider"]] = relationship(back_populates="title")
    interactions: Mapped[list["Interaction"]] = relationship(back_populates="title")
    embedding: Mapped["TitleEmbedding | None"] = relationship(back_populates="title", uselist=False)


class TitleGenre(Base):
    __tablename__ = "title_genres"

    title_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("titles.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
    )

    title: Mapped["Title"] = relationship(back_populates="title_genres")
    genre: Mapped["Genre"] = relationship(back_populates="title_genres")
