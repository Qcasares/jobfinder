from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "0005_drafting_runs"
down_revision = "0004_candidate_document_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "drafting_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("review_item_id", sa.String(length=240), nullable=False),
        sa.Column("requested_by", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("draft_text", sa.Text(), nullable=True),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("claim_mappings", sa.JSON(), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("failure_reason", sa.String(length=120), nullable=True),
        sa.Column("failure_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_drafting_runs_review_item_id"),
        "drafting_runs",
        ["review_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_drafting_runs_review_item_id"), table_name="drafting_runs")
    op.drop_table("drafting_runs")
