import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.provider import StreamingProvider
    from app.models.title import Title
    from app.models.user import User


class TitleEmbedding(Base):
    __tablename__ = "title_embeddings"

    title_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("titles.id", ondelete="CASCADE"), primary_key=True
    )
    content_vector: Mapped[Any] = mapped_column(Vector(384), nullable=False)
    model_vector: Mapped[Any | None] = mapped_column(Vector(64), nullable=True)

    title: Mapped["Title"] = relationship(back_populates="embedding")


class UserEmbedding(Base):
    __tablename__ = "user_embeddings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    profile_vector: Mapped[Any | None] = mapped_column(Vector(384), nullable=True)
    model_vector: Mapped[Any | None] = mapped_column(Vector(64), nullable=True)

    user: Mapped["User"] = relationship(back_populates="embedding")


class UserStreamingAffinity(Base):
    __tablename__ = "user_streaming_affinity"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("streaming_providers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)

    user: Mapped["User"] = relationship(back_populates="streaming_affinities")
    provider: Mapped["StreamingProvider"] = relationship(back_populates="user_affinities")


class ModelVersion(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "model_versions"

    version: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trained_at: Mapped[datetime] = mapped_column(nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
