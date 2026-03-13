import sys
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def update_exercise_categories():
    """
    Update all exercises to set their category_id based on their category name
    """
    # Get database URL from environment or use default
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/workout_db")
    
    # Create SQLAlchemy engine and session
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get all distinct categories from exercises
        logger.info("Getting distinct categories from exercises...")
        categories = session.execute(text("""
            SELECT DISTINCT category FROM exercises WHERE category IS NOT NULL AND category != ''
        """)).fetchall()
        
        category_names = [category[0] for category in categories]
        logger.info(f"Found {len(category_names)} distinct categories: {category_names}")
        
        # For each category, check if it exists in exercise_categories
        for category_name in category_names:
            # Check if category exists in exercise_categories
            existing_category = session.execute(text("""
                SELECT id FROM exercise_categories WHERE name = :name
            """), {"name": category_name}).fetchone()
            
            category_id = None
            if existing_category:
                category_id = existing_category[0]
                logger.info(f"Found existing category '{category_name}' with ID {category_id}")
            else:
                # Create new category
                logger.info(f"Creating new category '{category_name}'")
                result = session.execute(text("""
                    INSERT INTO exercise_categories (name, description, created_at, updated_at)
                    VALUES (:name, :description, NOW(), NOW())
                    RETURNING id
                """), {
                    "name": category_name,
                    "description": f"{category_name} exercises"
                })
                category_id = result.fetchone()[0]
                logger.info(f"Created new category '{category_name}' with ID {category_id}")
            
            # Update all exercises with this category
            result = session.execute(text("""
                UPDATE exercises 
                SET category_id = :category_id
                WHERE category = :category_name AND (category_id IS NULL OR category_id != :category_id)
            """), {
                "category_id": category_id,
                "category_name": category_name
            })
            
            rows_updated = result.rowcount
            logger.info(f"Updated {rows_updated} exercises to use category '{category_name}' with ID {category_id}")
        
        session.commit()
        logger.info("Update completed successfully!")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Update failed: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    logger.info("Starting exercise category update...")
    update_exercise_categories()
    logger.info("Exercise category update completed.") 