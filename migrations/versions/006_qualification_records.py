"""Add immutable qualification decision history for synthetic leads."""

from alembic import op
import sqlalchemy as sa

revision = "006_qualification_records"
down_revision = "005_automation_membership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "qualification_records",
        sa.Column("sequence", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("lead_id", sa.Uuid(), sa.ForeignKey("leads.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_identity_id", sa.Uuid(), sa.ForeignKey("identities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("request_key", sa.Uuid(), nullable=False),
        sa.Column("stored_status", sa.String(16), nullable=False),
        sa.Column("decision", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("lead_id", "request_key", name="uq_qualification_request"),
        sa.CheckConstraint("stored_status IN ('new', 'qualified')", name="ck_qualification_stored_status"),
    )
    op.create_index("ix_qualification_lead_sequence", "qualification_records", ["lead_id", "sequence"])


def downgrade() -> None:
    op.drop_index("ix_qualification_lead_sequence", table_name="qualification_records")
    op.drop_table("qualification_records")
