"""Add human-approved sales follow-up requests."""

from alembic import op
import sqlalchemy as sa

revision = "004_followup_requests"
down_revision = "003_lead_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "followup_requests",

        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "lead_id",
            sa.Uuid(),
            sa.ForeignKey("leads.id", ondelete="RESTRICT"),
            nullable=False,
        ),

        sa.Column(
            "request_key",
            sa.Uuid(),
            nullable=False,
        ),

        sa.Column(
            "requested_by_identity_id",
            sa.Uuid(),
            sa.ForeignKey("identities.id", ondelete="RESTRICT"),
            nullable=False,
        ),

        sa.Column(
            "decided_by_identity_id",
            sa.Uuid(),
            sa.ForeignKey("identities.id", ondelete="RESTRICT"),
            nullable=True,
        ),

        sa.Column("status", sa.String(16), nullable=False),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'executed')",
            name="ck_followup_status",
        ),

        sa.UniqueConstraint(
            "lead_id",
            "request_key",
            name="uq_followup_request",
        ),
    )


def downgrade() -> None:
    op.drop_table("followup_requests")