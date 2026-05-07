from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "0004_candidate_document_records"
down_revision = "0003_policy_evidence_expiry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidate_document_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("document_type", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=240), nullable=False),
        sa.Column("storage_ref", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("consent_scope", sa.String(length=120), nullable=False),
        sa.Column("consent_recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retention_delete_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redaction_status", sa.String(length=40), nullable=False),
        sa.Column("extraction_approved", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_candidate_document_records_user_id"),
        "candidate_document_records",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_candidate_document_records_user_id"),
        table_name="candidate_document_records",
    )
    op.drop_table("candidate_document_records")
