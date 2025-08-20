"""add_security_fields_to_sources

Revision ID: dee30032eb56
Revises: 43612296b120
Create Date: 2025-08-20 16:22:12.747518

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dee30032eb56'
down_revision: Union[str, Sequence[str], None] = '43612296b120'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename existing status column to health_status
    op.alter_column('sources', 'status', new_column_name='health_status')
    
    # Add security fields to sources table
    op.add_column('sources', sa.Column('status', sa.String(), nullable=False, server_default='enabled'))
    op.add_column('sources', sa.Column('allowed_ips', sa.Text(), nullable=False, server_default='[]'))
    op.add_column('sources', sa.Column('max_eps', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('sources', sa.Column('block_on_exceed', sa.Boolean(), nullable=False, server_default='1'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove security fields from sources table
    op.drop_column('sources', 'block_on_exceed')
    op.drop_column('sources', 'max_eps')
    op.drop_column('sources', 'allowed_ips')
    op.drop_column('sources', 'status')
    
    # Rename health_status back to status
    op.alter_column('sources', 'health_status', new_column_name='status')
