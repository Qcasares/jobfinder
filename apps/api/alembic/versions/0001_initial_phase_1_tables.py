from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_initial_phase_1"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
        sa.UniqueConstraint("domain", name=op.f("uq_sources_domain")),
    )
    op.create_table(
        "job_postings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("company", sa.String(length=240), nullable=False),
        sa.Column("remote_type", sa.String(length=40), nullable=False),
        sa.Column("employment_type", sa.String(length=80), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(length=3), nullable=True),
        sa.Column("posted_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_through", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extraction_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_postings")),
    )
    op.create_index(
        "ix_job_postings_company_title", "job_postings", ["company", "title"], unique=False
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=160), nullable=False),
        sa.Column("actor_type", sa.String(length=40), nullable=False),
        sa.Column("actor_id", sa.String(length=200), nullable=False),
        sa.Column("correlation_id", sa.String(length=120), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
        sa.UniqueConstraint("event_hash", name=op.f("uq_audit_events_event_hash")),
    )
    op.create_index(op.f("ix_audit_events_correlation_id"), "audit_events", ["correlation_id"])
    op.create_table(
        "candidate_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("profile_name", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_candidate_profiles_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candidate_profiles")),
    )
    op.create_index(op.f("ix_candidate_profiles_user_id"), "candidate_profiles", ["user_id"])
    op.create_table(
        "search_criteria",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=240), nullable=True),
        sa.Column("remote_type", sa.String(length=40), nullable=False),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_search_criteria_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_search_criteria")),
    )
    op.create_index(op.f("ix_search_criteria_user_id"), "search_criteria", ["user_id"])
    op.create_table(
        "source_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("allowed_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("denied_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name=op.f("fk_source_policies_source_id_sources")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_policies")),
    )
    op.create_index(op.f("ix_source_policies_source_id"), "source_policies", ["source_id"])
    op.create_table(
        "candidate_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("candidate_profile_id", sa.String(length=36), nullable=False),
        sa.Column("evidence_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_candidate_evidence_candidate_profile_id_candidate_profiles"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candidate_evidence")),
    )
    op.create_index(
        op.f("ix_candidate_evidence_candidate_profile_id"),
        "candidate_evidence",
        ["candidate_profile_id"],
    )
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_posting_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("request_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["job_posting_id"],
            ["job_postings.id"],
            name=op.f("fk_approval_requests_job_posting_id_job_postings"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_approval_requests_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_requests")),
    )
    op.create_index(
        op.f("ix_approval_requests_job_posting_id"), "approval_requests", ["job_posting_id"]
    )
    op.create_index(op.f("ix_approval_requests_user_id"), "approval_requests", ["user_id"])
    op.create_table(
        "job_posting_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_posting_id", sa.String(length=36), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("external_id", sa.String(length=240), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extraction_method", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_posting_id"],
            ["job_postings.id"],
            name=op.f("fk_job_posting_sources_job_posting_id_job_postings"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name=op.f("fk_job_posting_sources_source_id_sources")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_posting_sources")),
        sa.UniqueConstraint("source_id", "source_url", name="uq_job_posting_sources_source_url"),
    )
    op.create_index(
        op.f("ix_job_posting_sources_job_posting_id"), "job_posting_sources", ["job_posting_id"]
    )
    op.create_index(op.f("ix_job_posting_sources_source_id"), "job_posting_sources", ["source_id"])
    op.create_table(
        "job_field_provenance",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_posting_id", sa.String(length=36), nullable=False),
        sa.Column("field_name", sa.String(length=120), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("extraction_method", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("raw_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_posting_id"],
            ["job_postings.id"],
            name=op.f("fk_job_field_provenance_job_posting_id_job_postings"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_field_provenance")),
    )
    op.create_index(
        op.f("ix_job_field_provenance_job_posting_id"), "job_field_provenance", ["job_posting_id"]
    )
    op.create_table(
        "job_scores",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_posting_id", sa.String(length=36), nullable=False),
        sa.Column("search_criteria_id", sa.String(length=36), nullable=False),
        sa.Column("total_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_posting_id"],
            ["job_postings.id"],
            name=op.f("fk_job_scores_job_posting_id_job_postings"),
        ),
        sa.ForeignKeyConstraint(
            ["search_criteria_id"],
            ["search_criteria.id"],
            name=op.f("fk_job_scores_search_criteria_id_search_criteria"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_scores")),
    )
    op.create_index(op.f("ix_job_scores_job_posting_id"), "job_scores", ["job_posting_id"])
    op.create_index(op.f("ix_job_scores_search_criteria_id"), "job_scores", ["search_criteria_id"])
    op.create_table(
        "source_policy_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_policy_id", sa.String(length=36), nullable=False),
        sa.Column("evidence_type", sa.String(length=80), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_policy_id"],
            ["source_policies.id"],
            name=op.f("fk_source_policy_evidence_source_policy_id_source_policies"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_policy_evidence")),
    )
    op.create_index(
        op.f("ix_source_policy_evidence_source_policy_id"),
        "source_policy_evidence",
        ["source_policy_id"],
    )
    op.create_table(
        "applications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_posting_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("approval_request_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("application_url", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["approval_request_id"],
            ["approval_requests.id"],
            name=op.f("fk_applications_approval_request_id_approval_requests"),
        ),
        sa.ForeignKeyConstraint(
            ["job_posting_id"],
            ["job_postings.id"],
            name=op.f("fk_applications_job_posting_id_job_postings"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_applications_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
    )
    op.create_index(op.f("ix_applications_job_posting_id"), "applications", ["job_posting_id"])
    op.create_index(op.f("ix_applications_user_id"), "applications", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_applications_user_id"), table_name="applications")
    op.drop_index(op.f("ix_applications_job_posting_id"), table_name="applications")
    op.drop_table("applications")
    op.drop_index(
        op.f("ix_source_policy_evidence_source_policy_id"), table_name="source_policy_evidence"
    )
    op.drop_table("source_policy_evidence")
    op.drop_index(op.f("ix_job_scores_search_criteria_id"), table_name="job_scores")
    op.drop_index(op.f("ix_job_scores_job_posting_id"), table_name="job_scores")
    op.drop_table("job_scores")
    op.drop_index(op.f("ix_job_field_provenance_job_posting_id"), table_name="job_field_provenance")
    op.drop_table("job_field_provenance")
    op.drop_index(op.f("ix_job_posting_sources_source_id"), table_name="job_posting_sources")
    op.drop_index(op.f("ix_job_posting_sources_job_posting_id"), table_name="job_posting_sources")
    op.drop_table("job_posting_sources")
    op.drop_index(op.f("ix_approval_requests_user_id"), table_name="approval_requests")
    op.drop_index(op.f("ix_approval_requests_job_posting_id"), table_name="approval_requests")
    op.drop_table("approval_requests")
    op.drop_index(
        op.f("ix_candidate_evidence_candidate_profile_id"), table_name="candidate_evidence"
    )
    op.drop_table("candidate_evidence")
    op.drop_index(op.f("ix_source_policies_source_id"), table_name="source_policies")
    op.drop_table("source_policies")
    op.drop_index(op.f("ix_search_criteria_user_id"), table_name="search_criteria")
    op.drop_table("search_criteria")
    op.drop_index(op.f("ix_candidate_profiles_user_id"), table_name="candidate_profiles")
    op.drop_table("candidate_profiles")
    op.drop_index(op.f("ix_audit_events_correlation_id"), table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_job_postings_company_title", table_name="job_postings")
    op.drop_table("job_postings")
    op.drop_table("sources")
    op.drop_table("users")
