"""Embedding and affinity tables."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "005_embeddings"
down_revision = "004_interactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "title_embeddings",
        sa.Column("title_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_vector", Vector(384), nullable=False),
        sa.Column("model_vector", Vector(64), nullable=True),
        sa.ForeignKeyConstraint(["title_id"], ["titles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("title_id"),
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_title_embeddings_content_vector
        ON title_embeddings USING ivfflat (content_vector vector_cosine_ops)
        WITH (lists = 100)
        """
    )

    op.create_table(
        "user_embeddings",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_vector", Vector(384), nullable=True),
        sa.Column("model_vector", Vector(64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "user_streaming_affinity",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["streaming_providers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "provider_id"),
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_title_embeddings_content_vector")
    op.drop_table("user_streaming_affinity")
    op.drop_table("user_embeddings")
    op.drop_table("title_embeddings")
