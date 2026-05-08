from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "0008_manual_handoff_records"
down_revision = "0007_final_review_packets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "manual_handoff_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_domain", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("trigger_type", sa.String(length=80), nullable=False),
        sa.Column("requested_by", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("detection_detail", sa.Text(), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_manual_handoff_records_run_id"),
        "manual_handoff_records",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_manual_handoff_records_source_domain"),
        "manual_handoff_records",
        ["source_domain"],
        unique=False,
    )
    op.create_index(
        op.f("ix_manual_handoff_records_status"),
        "manual_handoff_records",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_manual_handoff_records_status"), table_name="manual_handoff_records")
    op.drop_index(
        op.f("ix_manual_handoff_records_source_domain"),
        table_name="manual_handoff_records",
    )
    op.drop_index(op.f("ix_manual_handoff_records_run_id"), table_name="manual_handoff_records")
    op.drop_table("manual_handoff_records")
