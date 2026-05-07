from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "0006_autofill_packets"
down_revision = "0005_drafting_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "autofill_packets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("drafting_run_id", sa.String(length=36), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("requested_by", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("fields", sa.JSON(), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("failure_reason", sa.String(length=120), nullable=True),
        sa.Column("failure_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["drafting_run_id"], ["drafting_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_autofill_packets_drafting_run_id"),
        "autofill_packets",
        ["drafting_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_autofill_packets_drafting_run_id"), table_name="autofill_packets")
    op.drop_table("autofill_packets")
