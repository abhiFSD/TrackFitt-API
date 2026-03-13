from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment or use default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/workout_db")

# Create a connection to the database
engine = create_engine(DATABASE_URL)

# SQL statements to execute
statements = [
    # Add rest_time_seconds column to workout_exercises
    "ALTER TABLE workout_exercises ADD COLUMN IF NOT EXISTS rest_time_seconds INTEGER",
    
    # Add rest_time_seconds column to workout_history_exercises
    "ALTER TABLE workout_history_exercises ADD COLUMN IF NOT EXISTS rest_time_seconds INTEGER",
    
    # Add rest_time_seconds column to scheduled_workout_exercises
    "ALTER TABLE scheduled_workout_exercises ADD COLUMN IF NOT EXISTS rest_time_seconds INTEGER",
    
    # Create workout_exercise_sets table
    """
    CREATE TABLE IF NOT EXISTS workout_exercise_sets (
        id SERIAL PRIMARY KEY,
        workout_exercise_id INTEGER NOT NULL REFERENCES workout_exercises(id) ON DELETE CASCADE,
        set_number INTEGER NOT NULL,
        reps INTEGER NOT NULL,
        weight FLOAT,
        rest_time_seconds INTEGER
    )
    """,
    
    # Create workout_history_exercise_sets table
    """
    CREATE TABLE IF NOT EXISTS workout_history_exercise_sets (
        id SERIAL PRIMARY KEY,
        workout_history_exercise_id INTEGER NOT NULL REFERENCES workout_history_exercises(id) ON DELETE CASCADE,
        set_number INTEGER NOT NULL,
        planned_reps INTEGER NOT NULL,
        planned_weight FLOAT,
        actual_reps INTEGER,
        actual_weight FLOAT,
        rest_time_seconds INTEGER,
        completion_time TIMESTAMP WITH TIME ZONE,
        duration_seconds INTEGER
    )
    """,
    
    # Create scheduled_workout_exercise_sets table
    """
    CREATE TABLE IF NOT EXISTS scheduled_workout_exercise_sets (
        id SERIAL PRIMARY KEY,
        scheduled_workout_exercise_id INTEGER NOT NULL REFERENCES scheduled_workout_exercises(id) ON DELETE CASCADE,
        set_number INTEGER NOT NULL,
        reps INTEGER NOT NULL,
        weight FLOAT,
        rest_time_seconds INTEGER
    )
    """
]

def execute_migrations():
    with engine.connect() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
                print(f"Successfully executed: {statement[:50]}...")
            except Exception as e:
                print(f"Error executing: {statement[:50]}...\nError: {str(e)}")
        connection.commit()

if __name__ == "__main__":
    print("Starting database migrations...")
    execute_migrations()
    print("Database migrations completed.") 