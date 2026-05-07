from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "0007_final_review_packets"
down_revision = "0006_autofill_packets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "final_review_packets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("autofill_packet_id", sa.String(length=36), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("requested_by", sa.String(length=200), nullable=False),
        sa.Column("operator_confirmation", sa.String(length=80), nullable=False),
        sa.Column("rollback_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("failure_reason", sa.String(length=120), nullable=True),
        sa.Column("failure_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["autofill_packet_id"], ["autofill_packets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_final_review_packets_autofill_packet_id"),
        "final_review_packets",
        ["autofill_packet_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_final_review_packets_autofill_packet_id"),
        table_name="final_review_packets",
    )
    op.drop_table("final_review_packets")
