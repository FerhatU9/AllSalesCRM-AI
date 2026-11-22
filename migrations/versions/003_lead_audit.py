"""Add organization-scoped lead activity history.

Revision ID: 003_lead_audit
Revises: 002_scoped_leads
"""

from alembic import op
import sqlalchemy as sa

revision = "003_lead_audit"
down_revision = "002_scoped_leads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lead_audit_events",
        sa.Column("sequence", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("id", sa.Uuid(), unique=True, nullable=False),
        sa.Column(
            "organization_id", sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "lead_id", sa.Uuid(),
            sa.ForeignKey("leads.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "actor_identity_id", sa.Uuid(),
            sa.ForeignKey("identities.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("changed_fields", sa.JSON(), nullable=False),
        sa.Column("previous_status", sa.String(length=16), nullable=True),
        sa.Column("new_status", sa.String(length=16), nullable=True),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("action IN ('created', 'updated')", name="ck_lead_audit_action"),
    )
    op.create_index(
        "ix_lead_audit_org_lead", "lead_audit_events",
        ["organization_id", "lead_id", "sequence"],
    )


def downgrade() -> None:
    op.drop_index("ix_lead_audit_org_lead", table_name="lead_audit_events")
    op.drop_table("lead_audit_events")
