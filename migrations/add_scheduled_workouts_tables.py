from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

"""
Migration to add scheduled_workouts and scheduled_workout_exercises tables
"""

def upgrade():
    # Create scheduled_workouts table
    op.create_table(
        'scheduled_workouts',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('workout_template_id', sa.Integer(), sa.ForeignKey('workouts.id'), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create scheduled_workout_exercises table
    op.create_table(
        'scheduled_workout_exercises',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('scheduled_workout_id', sa.Integer(), sa.ForeignKey('scheduled_workouts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('exercise_id', sa.Integer(), sa.ForeignKey('exercises.id'), nullable=False),
        sa.Column('sets', sa.Integer(), nullable=False),
        sa.Column('reps', sa.Integer(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )
    
    # Create indexes
    op.create_index('idx_scheduled_workouts_user_id', 'scheduled_workouts', ['user_id'])
    op.create_index('idx_scheduled_workouts_date', 'scheduled_workouts', ['scheduled_date'])
    op.create_index('idx_scheduled_workout_exercises_workout_id', 'scheduled_workout_exercises', ['scheduled_workout_id'])

def downgrade():
    # Drop tables in reverse order
    op.drop_table('scheduled_workout_exercises')
    op.drop_table('scheduled_workouts') 