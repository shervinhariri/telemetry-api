"""add_sources_table

Revision ID: 43612296b120
Revises: 5d64a5b83c8a
Create Date: 2025-08-19 23:41:20.474299

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43612296b120'
down_revision: Union[str, Sequence[str], None] = '5d64a5b83c8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create sources table
    op.create_table('sources',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('collector', sa.String(), nullable=False),
        sa.Column('site', sa.String(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_sources_tenant', 'sources', ['tenant_id'])
    op.create_index('idx_sources_status', 'sources', ['status'])
    op.create_index('idx_sources_last_seen', 'sources', ['last_seen'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_sources_last_seen', 'sources')
    op.drop_index('idx_sources_status', 'sources')
    op.drop_index('idx_sources_tenant', 'sources')
    
    # Drop table
    op.drop_table('sources')
