"""initial schema"""
from alembic import op
import sqlalchemy as sa

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('users', sa.Column('id', sa.String(36), primary_key=True), sa.Column('name', sa.String(120), nullable=False), sa.Column('email', sa.String(255), nullable=False), sa.Column('password_hash', sa.String(255), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_table('groups', sa.Column('id', sa.String(36), primary_key=True), sa.Column('name', sa.String(120), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_table('group_members', sa.Column('group_id', sa.String(36), sa.ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True), sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True), sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False))
    op.create_table('expense_events', sa.Column('id', sa.String(36), primary_key=True), sa.Column('group_id', sa.String(36), sa.ForeignKey('groups.id'), nullable=False), sa.Column('payer_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False), sa.Column('title', sa.String(160), nullable=False), sa.Column('status', sa.Enum('DRAFT', 'COMPLETED', name='eventstatus'), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.Column('completed_at', sa.DateTime(timezone=True)))
    op.create_index('ix_expense_events_group_id', 'expense_events', ['group_id'])
    op.create_table('event_members', sa.Column('event_id', sa.String(36), sa.ForeignKey('expense_events.id', ondelete='CASCADE'), primary_key=True), sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True))
    op.create_table('bills', sa.Column('id', sa.String(36), primary_key=True), sa.Column('event_id', sa.String(36), sa.ForeignKey('expense_events.id', ondelete='CASCADE'), nullable=False), sa.Column('category', sa.String(40), nullable=False), sa.Column('description', sa.String(160), nullable=False), sa.Column('amount', sa.Numeric(12, 2), nullable=False), sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False), sa.Column('receipt_name', sa.String(255)), sa.Column('split_method', sa.String(20), nullable=False, server_default='EQUAL'), sa.Column('split_allocations', sa.Text()))
    op.create_index('ix_bills_event_id', 'bills', ['event_id'])
    op.create_table('bill_participants', sa.Column('bill_id', sa.String(36), sa.ForeignKey('bills.id', ondelete='CASCADE'), primary_key=True), sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True))
    op.create_table('billing_requests', sa.Column('id', sa.String(36), primary_key=True), sa.Column('group_id', sa.String(36), sa.ForeignKey('groups.id', ondelete='CASCADE'), nullable=False), sa.Column('requester_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False), sa.Column('recipient_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False), sa.Column('event_id', sa.String(36), sa.ForeignKey('expense_events.id', ondelete='SET NULL')), sa.Column('bill_id', sa.String(36), sa.ForeignKey('bills.id', ondelete='SET NULL')), sa.Column('amount', sa.Numeric(12, 2), nullable=False), sa.Column('note', sa.String(160), nullable=False), sa.Column('status', sa.Enum('PENDING', 'COMPLETED', 'CANCELLED', name='requeststatus'), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_billing_requests_group_id', 'billing_requests', ['group_id'])

def downgrade():
    op.drop_index('ix_billing_requests_group_id', table_name='billing_requests'); op.drop_table('billing_requests'); op.drop_table('bill_participants'); op.drop_index('ix_bills_event_id', table_name='bills'); op.drop_table('bills'); op.drop_table('event_members'); op.drop_index('ix_expense_events_group_id', table_name='expense_events'); op.drop_table('expense_events'); op.drop_table('group_members'); op.drop_table('groups'); op.drop_index('ix_users_email', table_name='users'); op.drop_table('users')
