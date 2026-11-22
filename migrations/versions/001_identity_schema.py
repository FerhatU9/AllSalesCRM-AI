"""Create identities, organizations and scoped memberships.

Revision ID: 001_identity_schema
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "001_identity_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=160), nullable=False),
    )
    op.create_table(
        "identities",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("issuer", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("issuer", "subject", name="uq_identity_issuer_subject"),
    )
    op.create_table(
        "memberships",
        sa.Column(
            "organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            primary_key=True, nullable=False,
        ),
        sa.Column(
            "identity_id", sa.Uuid(), sa.ForeignKey("identities.id", ondelete="CASCADE"),
            primary_key=True, nullable=False,
        ),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.CheckConstraint("role IN ('owner', 'admin', 'sales', 'viewer')", name="ck_membership_role"),
    )


def downgrade() -> None:
    op.drop_table("memberships")
    op.drop_table("identities")
    op.drop_table("organizations")
