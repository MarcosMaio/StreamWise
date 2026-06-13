"""Core catalog tables."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "002_core_catalog"
down_revision = "001_enable_pgvector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "genres",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("tmdb_genre_id", sa.Integer(), nullable=True),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("tmdb_genre_id"),
    )

    op.create_table(
        "titles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("movielens_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=10), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("poster_path", sa.String(length=255), nullable=True),
        sa.Column("tmdb_popularity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("streamwise_avg_rating", sa.Float(), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_trending", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_new_release", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tmdb_id"),
        sa.UniqueConstraint("movielens_id"),
    )
    op.create_index("ix_titles_tmdb_id", "titles", ["tmdb_id"])
    op.create_index("ix_titles_is_trending", "titles", ["is_trending"])
    op.create_index("ix_titles_is_new_release", "titles", ["is_new_release"])
    op.create_index("ix_titles_tmdb_popularity", "titles", [sa.text("tmdb_popularity DESC")])

    op.create_table(
        "title_genres",
        sa.Column("title_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("genre_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["genre_id"], ["genres.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["title_id"], ["titles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("title_id", "genre_id"),
    )

    op.create_table(
        "streaming_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tmdb_provider_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("logo_path", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("tmdb_provider_id"),
    )

    op.create_table(
        "title_streaming_providers",
        sa.Column("title_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False, server_default="BR"),
        sa.Column("availability_type", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["streaming_providers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["title_id"], ["titles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("title_id", "provider_id", "country_code", "availability_type"),
    )


def downgrade() -> None:
    op.drop_table("title_streaming_providers")
    op.drop_table("streaming_providers")
    op.drop_table("title_genres")
    op.drop_index("ix_titles_tmdb_popularity", table_name="titles")
    op.drop_index("ix_titles_is_new_release", table_name="titles")
    op.drop_index("ix_titles_is_trending", table_name="titles")
    op.drop_index("ix_titles_tmdb_id", table_name="titles")
    op.drop_table("titles")
    op.drop_table("genres")
