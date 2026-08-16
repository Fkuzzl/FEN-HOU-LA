"""track manual confirmation of each participant share"""

from alembic import op
import sqlalchemy as sa

revision = "0005_bill_share_confirmations"
down_revision = "0004_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bill_share_confirmations",
        sa.Column("bill_id", sa.String(length=36), nullable=False),
        sa.Column("participant_id", sa.String(length=36), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["bill_id"], ["bills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("bill_id", "participant_id"),
    )


def downgrade() -> None:
    op.drop_table("bill_share_confirmations")
