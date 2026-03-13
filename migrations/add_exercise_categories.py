import sys
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, func, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import Base
from app.models.models import ExerciseCategory

# Get the database URL from environment variable or use default
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@db:5432/workout_db")

def migrate():
    """Add exercise_categories table and update exercises table with category_id and relationship"""
    engine = create_engine(DATABASE_URL)
    
    # Create the exercise_categories table if it doesn't exist
    with engine.begin() as conn:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Check if exercise_categories table already exists
        if "exercise_categories" not in tables:
            print("Creating exercise_categories table...")
            conn.execute(text("""
                CREATE TABLE exercise_categories (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                CREATE INDEX idx_exercise_category_name ON exercise_categories (name);
            """))
            print("exercise_categories table created successfully")
        else:
            print("exercise_categories table already exists")
        
        # Check if exercises table exists
        if "exercises" in tables:
            # Check if category_id column exists in exercises table
            columns = [c["name"] for c in inspector.get_columns("exercises")]
            if "category_id" not in columns:
                print("Adding category_id column to exercises table...")
                conn.execute(text("""
                    ALTER TABLE exercises ADD COLUMN category_id INTEGER;
                    ALTER TABLE exercises ADD CONSTRAINT fk_exercise_category 
                        FOREIGN KEY (category_id) REFERENCES exercise_categories(id);
                """))
                print("category_id column added successfully")
            else:
                print("category_id column already exists in exercises table")
        else:
            print("Warning: exercises table does not exist")
    
    # Create session for data migration
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if we have exercises with categories but no category_id
        result = db.execute(text("""
            SELECT DISTINCT category FROM exercises 
            WHERE category IS NOT NULL AND category != '' AND category_id IS NULL
        """))
        
        # Migrate category names to category_id relation
        for row in result:
            category_name = row[0]
            # Check if this category exists in exercise_categories
            category = db.query(ExerciseCategory).filter(ExerciseCategory.name == category_name).first()
            
            if not category:
                # Create new category
                category = ExerciseCategory(name=category_name)
                db.add(category)
                db.flush()  # To get the id
                print(f"Created new category: {category_name} with id {category.id}")
            
            # Update all exercises with this category name to use the category_id
            db.execute(text(f"""
                UPDATE exercises SET category_id = {category.id}
                WHERE category = '{category_name}' AND category_id IS NULL
            """))
            print(f"Updated exercises with category '{category_name}' to use category_id {category.id}")
        
        db.commit()
        print("Data migration completed successfully")
    except Exception as e:
        db.rollback()
        print(f"Error during data migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate() 