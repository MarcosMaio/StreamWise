"""P2 features: certification, content filters, bandit events, catalog snapshots."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "008_p2_features"
down_revision = "007_series_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("titles", sa.Column("certification", sa.String(length=10), nullable=True))

    op.create_table(
        "user_content_filters",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("blocked_genre_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("max_certification", sa.String(length=10), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "bandit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("is_exploration", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["title_id"], ["titles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_bandit_events_user_id", "bandit_events", ["user_id"])

    op.create_table(
        "provider_availability_snapshots",
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("title_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("availability_type", sa.String(length=20), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False, server_default="BR"),
        sa.ForeignKeyConstraint(["provider_id"], ["streaming_providers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["title_id"], ["titles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "snapshot_date", "title_id", "provider_id", "availability_type", "country_code"
        ),
    )

    op.create_table(
        "catalog_provider_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title_name", sa.String(length=500), nullable=False),
        sa.Column("provider_name", sa.String(length=100), nullable=False),
        sa.Column("change_type", sa.String(length=10), nullable=False),
        sa.Column("availability_type", sa.String(length=20), nullable=False, server_default="flatrate"),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["streaming_providers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["title_id"], ["titles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_catalog_changes_detected_at", "catalog_provider_changes", ["detected_at"])


def downgrade() -> None:
    op.drop_index("ix_catalog_changes_detected_at", table_name="catalog_provider_changes")
    op.drop_table("catalog_provider_changes")
    op.drop_table("provider_availability_snapshots")
    op.drop_index("ix_bandit_events_user_id", table_name="bandit_events")
    op.drop_table("bandit_events")
    op.drop_table("user_content_filters")
    op.drop_column("titles", "certification")
