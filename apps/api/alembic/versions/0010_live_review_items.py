from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "0010_live_review_items"
down_revision = "0009_operator_control_plane"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "live_review_items",
        sa.Column("id", sa.String(length=240), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("external_id", sa.String(length=240), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("application_url", sa.Text(), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("company", sa.String(length=240), nullable=False),
        sa.Column("locations", sa.JSON(), nullable=False),
        sa.Column("remote_type", sa.String(length=40), nullable=False),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(length=3), nullable=True),
        sa.Column("employment_type", sa.String(length=80), nullable=True),
        sa.Column("posted_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_through", sa.DateTime(timezone=True), nullable=True),
        sa.Column("required_skills", sa.JSON(), nullable=False),
        sa.Column("preferred_skills", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(length=40), nullable=False),
        sa.Column("review_reasons", sa.JSON(), nullable=False),
        sa.Column("extraction_confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("provenance_hints", sa.JSON(), nullable=False),
        sa.Column("data_origin", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_url", name=op.f("uq_live_review_items_source_url")),
    )
    op.create_index(
        op.f("ix_live_review_items_review_status"),
        "live_review_items",
        ["review_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_live_review_items_source"),
        "live_review_items",
        ["source"],
        unique=False,
    )
    op.create_index(
        "ix_live_review_items_source_created",
        "live_review_items",
        ["source", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_live_review_items_source_created", table_name="live_review_items")
    op.drop_index(op.f("ix_live_review_items_source"), table_name="live_review_items")
    op.drop_index(op.f("ix_live_review_items_review_status"), table_name="live_review_items")
    op.drop_table("live_review_items")
