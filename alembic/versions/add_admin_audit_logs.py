"""Add admin audit logs table

Revision ID: add_admin_audit_logs
Revises: 5d64a5b83c8a
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_admin_audit_logs'
down_revision = '5d64a5b83c8a'
branch_labels = None
depends_on = None


def upgrade():
    # Create admin_audit_logs table
    op.create_table('admin_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('actor_key_id', sa.String(255), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('target', sa.String(255), nullable=False),
        sa.Column('before_value', sa.Text(), nullable=True),
        sa.Column('after_value', sa.Text(), nullable=True),
        sa.Column('client_ip', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient querying
    op.create_index('ix_admin_audit_logs_timestamp', 'admin_audit_logs', ['timestamp'])
    op.create_index('ix_admin_audit_logs_actor_key_id', 'admin_audit_logs', ['actor_key_id'])
    op.create_index('ix_admin_audit_logs_action', 'admin_audit_logs', ['action'])


def downgrade():
    op.drop_index('ix_admin_audit_logs_action', table_name='admin_audit_logs')
    op.drop_index('ix_admin_audit_logs_actor_key_id', table_name='admin_audit_logs')
    op.drop_index('ix_admin_audit_logs_timestamp', table_name='admin_audit_logs')
    op.drop_table('admin_audit_logs')
