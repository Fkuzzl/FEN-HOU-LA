"""username login, group ownership, participant roles, and request audit fields"""
from alembic import op
import sqlalchemy as sa

revision = "0003_accounts_participants"
down_revision = "0002_invites"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("username", sa.String(40), nullable=True))
    op.execute("UPDATE users SET username = substr(email, 1, 40) WHERE username IS NULL")
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("groups") as batch:
            batch.add_column(sa.Column("owner_id", sa.String(36), nullable=True))
            batch.create_foreign_key("fk_groups_owner_id", "users", ["owner_id"], ["id"])
    else:
        op.add_column("groups", sa.Column("owner_id", sa.String(36), nullable=True))
        op.create_foreign_key("fk_groups_owner_id", "groups", "users", ["owner_id"], ["id"])
    op.execute("UPDATE groups SET owner_id = (SELECT user_id FROM group_members WHERE group_members.group_id = groups.id LIMIT 1) WHERE owner_id IS NULL")
    op.create_table(
        "participants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("group_id", sa.String(36), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_participants_group_id", "participants", ["group_id"])
    op.create_index("ix_participants_user_id", "participants", ["user_id"])
    op.create_table(
        "bill_participant_roles",
        sa.Column("bill_id", sa.String(36), sa.ForeignKey("bills.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("participant_id", sa.String(36), sa.ForeignKey("participants.id", ondelete="CASCADE"), primary_key=True),
    )
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("billing_requests") as batch:
            batch.add_column(sa.Column("participant_id", sa.String(36), nullable=True))
            batch.add_column(sa.Column("completed_by", sa.String(36), nullable=True))
            batch.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
            batch.create_foreign_key("fk_billing_requests_participant_id", "participants", ["participant_id"], ["id"], ondelete="SET NULL")
            batch.create_foreign_key("fk_billing_requests_completed_by", "users", ["completed_by"], ["id"])
    else:
        op.add_column("billing_requests", sa.Column("participant_id", sa.String(36), sa.ForeignKey("participants.id", ondelete="SET NULL")))
        op.add_column("billing_requests", sa.Column("completed_by", sa.String(36), sa.ForeignKey("users.id")))
        op.add_column("billing_requests", sa.Column("completed_at", sa.DateTime(timezone=True)))


def downgrade():
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("billing_requests") as batch:
            batch.drop_constraint("fk_billing_requests_completed_by", type_="foreignkey")
            batch.drop_constraint("fk_billing_requests_participant_id", type_="foreignkey")
            batch.drop_column("completed_at")
            batch.drop_column("completed_by")
            batch.drop_column("participant_id")
    else:
        op.drop_column("billing_requests", "completed_at")
        op.drop_column("billing_requests", "completed_by")
        op.drop_column("billing_requests", "participant_id")
    op.drop_table("bill_participant_roles")
    op.drop_index("ix_participants_user_id", table_name="participants")
    op.drop_index("ix_participants_group_id", table_name="participants")
    op.drop_table("participants")
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("groups") as batch:
            batch.drop_constraint("fk_groups_owner_id", type_="foreignkey")
            batch.drop_column("owner_id")
    else:
        op.drop_constraint("fk_groups_owner_id", "groups", type_="foreignkey")
        op.drop_column("groups", "owner_id")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "username")
