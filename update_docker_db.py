from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

# Use the Docker database URL
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/workout_db"

def update_docker_database():
    # Create SQLAlchemy engine
    engine = create_engine(DATABASE_URL)
    
    # Connect to the database
    with engine.connect() as connection:
        # Check if column exists first to avoid errors if it's already there
        check_column_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name = 'workouts' AND column_name = 'is_published'")
        result = connection.execute(check_column_sql)
        column_exists = result.fetchone() is not None
        
        if not column_exists:
            # Add is_published column with default value of False
            add_column_sql = text("ALTER TABLE workouts ADD COLUMN is_published BOOLEAN DEFAULT FALSE")
            connection.execute(add_column_sql)
            print("Successfully added is_published column to workouts table in Docker")
        else:
            print("Column is_published already exists in workouts table in Docker")
        
        # Commit the transaction
        connection.commit()

if __name__ == "__main__":
    update_docker_database() 