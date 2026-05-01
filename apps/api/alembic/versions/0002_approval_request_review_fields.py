from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "0002_approval_review_fields"
down_revision = "0001_initial_phase_1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "approval_requests",
        sa.Column("review_item_id", sa.String(length=240), nullable=True),
    )
    op.add_column(
        "approval_requests",
        sa.Column("requester_id", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "approval_requests",
        sa.Column("reviewer_id", sa.String(length=200), nullable=True),
    )
    op.create_index(
        op.f("ix_approval_requests_review_item_id"),
        "approval_requests",
        ["review_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_approval_requests_review_item_id"), table_name="approval_requests")
    op.drop_column("approval_requests", "reviewer_id")
    op.drop_column("approval_requests", "requester_id")
    op.drop_column("approval_requests", "review_item_id")
