from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "0003_policy_evidence_expiry"
down_revision = "0002_approval_review_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "source_policy_evidence",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("source_policy_evidence", "expires_at")
