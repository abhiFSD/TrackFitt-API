import sys
import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.models import Base, User as DBUser, UserRole as DBUserRole
from app.api.auth import get_password_hash

# Get the database URL from environment variable or use default
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@db:5432/workout_db")

def wait_for_db(engine, max_retries=30, retry_interval=2):
    """Wait for the database to be ready."""
    retries = 0
    while retries < max_retries:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                print("Database connection successful!")
                return True
        except OperationalError as e:
            print(f"Database not ready yet: {e}")
            retries += 1
            print(f"Retry {retries}/{max_retries} in {retry_interval} seconds...")
            time.sleep(retry_interval)
    
    print("Failed to connect to the database after maximum retries")
    return False

def init_db():
    """Initialize the database with tables and initial data."""
    engine = create_engine(DATABASE_URL)
    
    if not wait_for_db(engine):
        sys.exit(1)
    
    # Create tables (COMMENTED OUT - Use Alembic migrations instead)
    # Base.metadata.create_all(bind=engine)
    # print("Tables created successfully")
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # Check if admin user exists
    admin_user = db.query(DBUser).filter(DBUser.username == "admin").first()
    if not admin_user:
        # Create admin user
        admin_password = get_password_hash("admin123")
        admin_user = DBUser(
            username="admin",
            email="admin@example.com",
            hashed_password=admin_password,
            role=DBUserRole.ADMIN,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        print("Admin user created successfully")
    else:
        print("Admin user already exists")
    
    # After creating tables, add the profile_image_url column if it doesn't exist
    with engine.begin() as conn:
        # Check if column exists first
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='user_profiles' AND column_name='profile_image_url'"))
        if result.fetchone() is None:
            print("Adding profile_image_url column to user_profiles table...")
            conn.execute(text("ALTER TABLE user_profiles ADD COLUMN profile_image_url VARCHAR;"))
            print("Column added successfully.")
        else:
            print("Column profile_image_url already exists.")
    
    db.close()
    print("Database initialization completed")

if __name__ == "__main__":
    init_db() 