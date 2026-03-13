from sqlalchemy import Column, Boolean
from alembic import op
import sqlalchemy as sa

"""
Migration to add is_published column to workouts table
"""

def upgrade():
    # Add is_published column with default value False
    op.add_column('workouts', sa.Column('is_published', sa.Boolean(), nullable=True, server_default='false'))

def downgrade():
    # Remove is_published column
    op.drop_column('workouts', 'is_published') 