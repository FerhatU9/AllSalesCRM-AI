"""Add restricted automation membership role."""

from alembic import op
import sqlalchemy as sa


revision = "005_automation_membership"
down_revision = "004_followup_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("memberships") as batch:
        batch.drop_constraint(
            "ck_membership_role",
            type_="check",
        )

        batch.create_check_constraint(
            "ck_membership_role",
            "role IN ('owner', 'admin', 'sales', 'viewer', 'automation')",
        )


def downgrade() -> None:
    if not op.get_context().as_sql:
        count = op.get_bind().execute(
            sa.text(
                "SELECT COUNT(*) FROM memberships "
                "WHERE role = 'automation'"
            )
        ).scalar_one()

        if count:
            raise RuntimeError(
                "Remove automation memberships before downgrade"
            )

    with op.batch_alter_table("memberships") as batch:
        batch.drop_constraint(
            "ck_membership_role",
            type_="check",
        )

        batch.create_check_constraint(
            "ck_membership_role",
            "role IN ('owner', 'admin', 'sales', 'viewer')",
        )