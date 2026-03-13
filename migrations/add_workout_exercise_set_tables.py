"""Add workout exercise set tables and columns

This migration adds the set details tables and rest time columns to support multiple
sets with different weights, reps, and tracking data.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Add rest_time_seconds column to workout_exercises
    op.add_column('workout_exercises', sa.Column('rest_time_seconds', sa.Integer(), nullable=True))
    
    # Create workout_exercise_sets table
    op.create_table('workout_exercise_sets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workout_exercise_id', sa.Integer(), nullable=False),
        sa.Column('set_number', sa.Integer(), nullable=False),
        sa.Column('reps', sa.Integer(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('rest_time_seconds', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['workout_exercise_id'], ['workout_exercises.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add rest_time_seconds column to workout_history_exercises
    op.add_column('workout_history_exercises', sa.Column('rest_time_seconds', sa.Integer(), nullable=True))
    
    # Create workout_history_exercise_sets table
    op.create_table('workout_history_exercise_sets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workout_history_exercise_id', sa.Integer(), nullable=False),
        sa.Column('set_number', sa.Integer(), nullable=False),
        sa.Column('planned_reps', sa.Integer(), nullable=False),
        sa.Column('planned_weight', sa.Float(), nullable=True),
        sa.Column('actual_reps', sa.Integer(), nullable=True),
        sa.Column('actual_weight', sa.Float(), nullable=True),
        sa.Column('rest_time_seconds', sa.Integer(), nullable=True),
        sa.Column('completion_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['workout_history_exercise_id'], ['workout_history_exercises.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add rest_time_seconds column to scheduled_workout_exercises
    op.add_column('scheduled_workout_exercises', sa.Column('rest_time_seconds', sa.Integer(), nullable=True))
    
    # Create scheduled_workout_exercise_sets table
    op.create_table('scheduled_workout_exercise_sets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scheduled_workout_exercise_id', sa.Integer(), nullable=False),
        sa.Column('set_number', sa.Integer(), nullable=False),
        sa.Column('reps', sa.Integer(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('rest_time_seconds', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['scheduled_workout_exercise_id'], ['scheduled_workout_exercises.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_table('scheduled_workout_exercise_sets')
    op.drop_column('scheduled_workout_exercises', 'rest_time_seconds')
    
    op.drop_table('workout_history_exercise_sets')
    op.drop_column('workout_history_exercises', 'rest_time_seconds')
    
    op.drop_table('workout_exercise_sets')
    op.drop_column('workout_exercises', 'rest_time_seconds') 