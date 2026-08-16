"""private local receipt metadata"""
from alembic import op
import sqlalchemy as sa

revision = "0004_receipts"
down_revision = "0003_accounts_participants"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("bills", sa.Column("receipt_key", sa.String(255)))
    op.add_column("bills", sa.Column("receipt_content_type", sa.String(100)))
    op.add_column("bills", sa.Column("receipt_size", sa.Integer()))


def downgrade():
    op.drop_column("bills", "receipt_size")
    op.drop_column("bills", "receipt_content_type")
    op.drop_column("bills", "receipt_key")
