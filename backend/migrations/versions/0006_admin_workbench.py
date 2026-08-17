"""add operator roles, safe group archiving, and admin audit logs"""

from alembic import op
import sqlalchemy as sa

revision = "0006_admin_workbench"
down_revision = "0005_bill_share_confirmations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("is_disabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("groups", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("admin_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=True),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("admin_audit_logs")
    op.drop_column("groups", "archived_at")
    op.drop_column("users", "is_disabled")
    op.drop_column("users", "is_admin")
