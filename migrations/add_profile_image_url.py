from sqlalchemy import create_engine, Column, String, MetaData, Table
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment variable or use default
database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/workout_db")

# Create engine and connect to the database
engine = create_engine(database_url)
metadata = MetaData()

# Define the user_profiles table
user_profiles = Table('user_profiles', metadata, autoload_with=engine)

def run_migration():
    with engine.begin() as conn:
        # Check if column already exists to avoid errors
        result = conn.execute("SELECT column_name FROM information_schema.columns WHERE table_name='user_profiles' AND column_name='profile_image_url'")
        if result.rowcount == 0:
            print("Adding profile_image_url column to user_profiles table...")
            conn.execute("ALTER TABLE user_profiles ADD COLUMN profile_image_url VARCHAR;")
            print("Column added successfully.")
        else:
            print("Column profile_image_url already exists.")

if __name__ == "__main__":
    run_migration() 