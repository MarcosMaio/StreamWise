import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserContentFilter(Base):
    __tablename__ = "user_content_filters"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    blocked_genre_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    max_certification: Mapped[str | None] = mapped_column(String(10), nullable=True)

    user: Mapped["User"] = relationship(back_populates="content_filter")


class BanditEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "bandit_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("titles.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_exploration: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class ProviderAvailabilitySnapshot(Base):
    __tablename__ = "provider_availability_snapshots"

    snapshot_date: Mapped[datetime] = mapped_column(Date, primary_key=True)
    title_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("titles.id", ondelete="CASCADE"), primary_key=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("streaming_providers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    availability_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    country_code: Mapped[str] = mapped_column(String(2), primary_key=True, default="BR")


class CatalogProviderChange(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "catalog_provider_changes"

    title_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("titles.id", ondelete="CASCADE"), nullable=False
    )
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("streaming_providers.id", ondelete="SET NULL"), nullable=True
    )
    title_name: Mapped[str] = mapped_column(String(500), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    change_type: Mapped[str] = mapped_column(String(10), nullable=False)
    availability_type: Mapped[str] = mapped_column(String(20), nullable=False, default="flatrate")
    detected_at: Mapped[datetime] = mapped_column(nullable=False)
