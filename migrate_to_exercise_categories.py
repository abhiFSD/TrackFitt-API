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

def run_migration():
    """
    Migrate all data from the old 'categories' table to 'exercise_categories'
    and update all references to use the new table.
    """
    # Get database URL from environment or use default
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/workout_db")
    
    # Create SQLAlchemy engine and session
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if both tables exist
        logger.info("Checking tables...")
        tables = session.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name IN ('categories', 'exercise_categories')
        """)).fetchall()
        
        table_names = [table[0] for table in tables]
        if 'categories' not in table_names:
            logger.info("Categories table does not exist. No migration needed.")
            return
        
        if 'exercise_categories' not in table_names:
            logger.error("exercise_categories table does not exist. Please run the create_exercise_categories migration first.")
            return
            
        # Get all categories from the old table
        logger.info("Fetching categories from legacy table...")
        categories = session.execute(text("""
            SELECT id, name, description, created_at, updated_at FROM categories
        """)).fetchall()
        
        if not categories:
            logger.info("No categories to migrate.")
        else:
            logger.info(f"Found {len(categories)} categories to migrate.")
            
            # For each category, find or create an equivalent in exercise_categories
            for category in categories:
                old_id = category[0]
                name = category[1]
                description = category[2]
                
                # Check if this category already exists in exercise_categories
                existing = session.execute(text("""
                    SELECT id FROM exercise_categories WHERE name = :name
                """), {"name": name}).fetchone()
                
                if existing:
                    new_id = existing[0]
                    logger.info(f"Category '{name}' already exists in exercise_categories with ID {new_id}")
                else:
                    # Insert the category into exercise_categories
                    result = session.execute(text("""
                        INSERT INTO exercise_categories (name, description, created_at, updated_at)
                        VALUES (:name, :description, :created_at, :updated_at)
                        RETURNING id
                    """), {
                        "name": name,
                        "description": description,
                        "created_at": category[3],
                        "updated_at": category[4]
                    })
                    new_id = result.fetchone()[0]
                    logger.info(f"Created category '{name}' in exercise_categories with ID {new_id}")
                
                # Update all references to this category in the exercises table
                # First, check if there are any exercises using this category
                count = session.execute(text("""
                    SELECT COUNT(*) FROM exercises WHERE category_id::text = :old_id
                """), {"old_id": str(old_id)}).fetchone()[0]
                
                if count > 0:
                    # Update the references
                    session.execute(text("""
                        UPDATE exercises 
                        SET category_id = :new_id
                        WHERE category_id::text = :old_id
                    """), {"new_id": new_id, "old_id": str(old_id)})
                    logger.info(f"Updated {count} exercises to use new category ID {new_id}")
            
            # After all migrations, you might want to drop the old table
            logger.info("Migration completed. You can now drop the 'categories' table if desired.")
            # Uncomment the line below to automatically drop the table after migration
            # session.execute(text("DROP TABLE categories"))
        
        session.commit()
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Migration failed: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    logger.info("Starting migration from categories to exercise_categories...")
    run_migration()
    logger.info("Migration completed.") 