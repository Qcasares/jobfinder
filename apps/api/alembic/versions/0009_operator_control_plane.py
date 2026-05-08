from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "0009_operator_control_plane"
down_revision = "0008_manual_handoff_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_queue_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_domain", sa.String(length=255), nullable=False),
        sa.Column("requested_by", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("max_results", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("rate_limit_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("live_run_id", sa.String(length=36), nullable=True),
        sa.Column("manual_handoff_id", sa.String(length=36), nullable=True),
        sa.Column("failure_reason", sa.String(length=120), nullable=True),
        sa.Column("failure_detail", sa.Text(), nullable=True),
        sa.Column("discovered_urls", sa.JSON(), nullable=False),
        sa.Column("review_item_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_discovery_queue_runs_live_run_id"),
        "discovery_queue_runs",
        ["live_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_queue_runs_manual_handoff_id"),
        "discovery_queue_runs",
        ["manual_handoff_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_queue_runs_source_domain"),
        "discovery_queue_runs",
        ["source_domain"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_queue_runs_status"),
        "discovery_queue_runs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_discovery_queue_runs_domain_created",
        "discovery_queue_runs",
        ["source_domain", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_discovery_queue_runs_domain_created", table_name="discovery_queue_runs")
    op.drop_index(op.f("ix_discovery_queue_runs_status"), table_name="discovery_queue_runs")
    op.drop_index(
        op.f("ix_discovery_queue_runs_source_domain"),
        table_name="discovery_queue_runs",
    )
    op.drop_index(
        op.f("ix_discovery_queue_runs_manual_handoff_id"),
        table_name="discovery_queue_runs",
    )
    op.drop_index(op.f("ix_discovery_queue_runs_live_run_id"), table_name="discovery_queue_runs")
    op.drop_table("discovery_queue_runs")
