import sys
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

def run_migration():
    """
    Run the migration to add the exercise_categories table and category_id column to exercises.
    This preserves existing category data and creates corresponding category entries.
    """
    # Get database URL from environment or use default
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/workout_db")
    
    # Create SQLAlchemy engine and session
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Create exercise_categories table
        logger.info("Creating exercise_categories table...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS exercise_categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        
        # Add category_id column to exercises table
        logger.info("Adding category_id column to exercises table...")
        session.execute(text("""
            ALTER TABLE exercises 
            ADD COLUMN IF NOT EXISTS category_id INTEGER,
            ADD CONSTRAINT fk_exercise_category
            FOREIGN KEY (category_id) 
            REFERENCES exercise_categories(id)
        """))
        
        # Get existing distinct categories from exercises
        logger.info("Migrating existing categories...")
        categories = session.execute(text("""
            SELECT DISTINCT category FROM exercises 
            WHERE category IS NOT NULL AND category != ''
        """)).fetchall()
        
        # Insert distinct categories into the exercise_categories table
        for category_tuple in categories:
            category_name = category_tuple[0]
            if category_name:
                session.execute(text("""
                    INSERT INTO exercise_categories (name) 
                    VALUES (:name) 
                    ON CONFLICT (name) DO NOTHING
                """), {"name": category_name})
        
        # Update exercises to set category_id based on category name
        logger.info("Updating exercises with category_id...")
        session.execute(text("""
            UPDATE exercises e
            SET category_id = ec.id
            FROM exercise_categories ec
            WHERE e.category = ec.name
        """))
        
        session.commit()
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Migration failed: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    logger.info("Starting exercise categories migration...")
    run_migration()
    logger.info("Exercise categories migration completed.") 