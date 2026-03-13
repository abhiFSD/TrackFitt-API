import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/workout_db")

# Create engine
engine = create_engine(DATABASE_URL)

# SQL commands to add missing columns
alter_table_commands = [
    "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS exercise_id VARCHAR(255) UNIQUE",
    "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS category VARCHAR(255)",
    "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS muscle_groups TEXT",
    "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS difficulty VARCHAR(255)",
    "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS equipment VARCHAR(255)",
    "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS instructions TEXT",
    "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS image_url VARCHAR(255)",
    "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS video_url VARCHAR(255)",
    "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS form_tips TEXT",
    "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS common_mistakes TEXT",
    "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS variations TEXT",
    "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE"
]

def update_exercise_table():
    print(f"Connecting to database: {DATABASE_URL.split('@')[-1]}")
    
    with engine.connect() as connection:
        print("Connection successful")
        
        # Execute ALTER TABLE commands to add missing columns
        for cmd in alter_table_commands:
            print(f"Executing: {cmd}")
            connection.execute(text(cmd))
            connection.commit()
        
        print("Exercise table update completed.")

if __name__ == "__main__":
    update_exercise_table() 