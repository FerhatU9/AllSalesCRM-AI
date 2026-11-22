"""Add organization-scoped synthetic lead records.

Revision ID: 002_scoped_leads
Revises: 001_identity_schema
"""
from alembic import op
import sqlalchemy as sa

revision = "002_scoped_leads"
down_revision = "001_identity_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id", sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "created_by_identity_id", sa.Uuid(),
            sa.ForeignKey("identities.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("company_name", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.CheckConstraint("status IN ('new', 'qualified', 'archived')", name="ck_lead_status"),
    )
    op.create_index("ix_leads_org_id", "leads", ["organization_id", "id"])


def downgrade() -> None:
    op.drop_index("ix_leads_org_id", table_name="leads")
    op.drop_table("leads")
