import os
import csv
import json
from datetime import datetime
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from app.db.database import Base
from app.models.models import Exercise, ExerciseCategory
from dotenv import load_dotenv
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Define the database URL - use the same one as in app/db/database.py
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/workout_db")

logger.info(f"Using database: {DATABASE_URL.split('@')[-1]}")

try:
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Test connection
    with engine.connect() as conn:
        logger.info("Database connection successful")
except OperationalError as e:
    logger.error(f"Failed to connect to database: {str(e)}")
    logger.error("Please check your database connection settings and make sure the database is running.")
    sys.exit(1)
except Exception as e:
    logger.error(f"Unexpected error connecting to database: {str(e)}")
    sys.exit(1)

def check_tables():
    """Check if tables exist in the database"""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Existing tables: {tables}")
        return "exercises" in tables
    except Exception as e:
        logger.error(f"Error checking tables: {str(e)}")
        return False

def import_exercises():
    """Import exercises from CSV file"""
    csv_path = os.path.join("dataCsv", "results.csv")
    
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found at {csv_path}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Looking for file: {os.path.abspath(csv_path)}")
        return
    
    logger.info(f"Importing exercises from {csv_path}...")
    
    db = SessionLocal()
    try:
        imported_count = 0
        updated_count = 0
        error_count = 0
        
        # Get all existing categories
        categories = {}
        for category in db.query(ExerciseCategory).all():
            categories[category.name] = category.id
        
        logger.info(f"Found {len(categories)} existing categories")
        
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            
            for row_num, row in enumerate(csv_reader, start=1):
                try:
                    # Check if exercise already exists by exercise_id
                    existing_exercise = db.query(Exercise).filter(
                        Exercise.exercise_id == row['exercise_id']
                    ).first()
                    
                    # Default dates to current time if parsing fails
                    current_time = datetime.now()
                    created_at = current_time
                    updated_at = current_time
                    
                    # Try to parse dates if they exist
                    if row.get('created_at') and not row['created_at'].startswith('{'):
                        try:
                            created_at = datetime.fromisoformat(row['created_at'])
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid created_at date format in row {row_num}: {row.get('created_at')}")
                    
                    if row.get('updated_at') and not row['updated_at'].startswith('{'):
                        try:
                            updated_at = datetime.fromisoformat(row['updated_at'])
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid updated_at date format in row {row_num}: {row.get('updated_at')}")
                    
                    # Handle category relationship
                    category_name = row['category']
                    category_id = None
                    
                    if category_name:
                        # Check if category exists
                        if category_name in categories:
                            category_id = categories[category_name]
                        else:
                            # Create new category
                            logger.info(f"Creating new category: {category_name}")
                            new_category = ExerciseCategory(
                                name=category_name,
                                description=f"{category_name} exercises",
                                created_at=created_at,
                                updated_at=updated_at
                            )
                            db.add(new_category)
                            db.flush()  # Flush to get the ID
                            
                            category_id = new_category.id
                            categories[category_name] = category_id
                            logger.info(f"Created category '{category_name}' with ID {category_id}")
                    
                    # Handle muscle_groups properly
                    muscle_groups = row.get('muscle_groups', '[]')
                    if isinstance(muscle_groups, str) and not muscle_groups.startswith('['):
                        # If it doesn't look like a JSON array, set it to empty array
                        logger.warning(f"Invalid muscle_groups format in row {row_num}: {muscle_groups}")
                        muscle_groups = '[]'
                    
                    exercise_data = {
                        "exercise_id": row['exercise_id'],
                        "name": row['name'],
                        "description": row.get('description', ''),
                        "category": category_name,
                        "category_id": category_id,  # Set the category_id
                        "muscle_groups": muscle_groups,
                        "difficulty": row.get('difficulty', ''),
                        "equipment": row.get('equipment', ''),
                        "instructions": row.get('instructions', ''),
                        "image_url": row.get('image_url', ''),
                        "video_url": row.get('video_url', ''),
                        "form_tips": row.get('form_tips', ''),
                        "common_mistakes": row.get('common_mistakes', ''),
                        "variations": row.get('variations', ''),
                        "created_at": created_at,
                        "updated_at": updated_at
                    }
                    
                    if existing_exercise:
                        # Update existing exercise
                        for key, value in exercise_data.items():
                            setattr(existing_exercise, key, value)
                        updated_count += 1
                    else:
                        # Create new exercise
                        db_exercise = Exercise(**exercise_data)
                        db.add(db_exercise)
                        imported_count += 1
                        
                    # Commit every 50 records to avoid large transactions
                    if (imported_count + updated_count) % 50 == 0:
                        db.commit()
                        logger.info(f"Progress: {imported_count + updated_count} exercises processed")
                
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing row {row_num}: {str(e)}")
                    if error_count > 10:
                        logger.error("Too many errors, aborting import process")
                        db.rollback()
                        return
            
            # Final commit
            db.commit()
            logger.info(f"Successfully imported {imported_count} new exercises and updated {updated_count} existing exercises")
            if error_count > 0:
                logger.warning(f"Encountered {error_count} errors during import")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error importing CSV: {str(e)}")
    finally:
        db.close()

def create_tables():
    """Create all database tables defined in models"""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully")
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error creating tables: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error creating tables: {str(e)}")
        sys.exit(1)

def main():
    """Main migration function"""
    logger.info("Starting exercise migration process...")
    
    # First, create tables if they don't exist
    if not check_tables():
        logger.info("Exercise table does not exist. Creating tables...")
        create_tables()
    
    # Then import exercises
    import_exercises()
    
    logger.info("Migration process completed")

if __name__ == "__main__":
    main() 