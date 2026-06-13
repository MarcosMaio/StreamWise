import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.embedding import UserEmbedding, UserStreamingAffinity
    from app.models.interaction import Interaction, UserPreference, UserSeriesProgress


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="BR")
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(back_populates="user")
    interactions: Mapped[list["Interaction"]] = relationship(back_populates="user")
    preferences: Mapped[list["UserPreference"]] = relationship(back_populates="user")
    streaming_affinities: Mapped[list["UserStreamingAffinity"]] = relationship(back_populates="user")
    embedding: Mapped["UserEmbedding | None"] = relationship(back_populates="user", uselist=False)
    series_progress: Mapped[list["UserSeriesProgress"]] = relationship(back_populates="user")


class OAuthAccount(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "oauth_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_account_id", name="uq_oauth_provider_account"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_account_id: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped["User"] = relationship(back_populates="oauth_accounts")
