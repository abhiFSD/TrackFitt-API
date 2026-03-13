import logging
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get database connection params from environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/workout_db")

# Parse the connection string
def parse_db_url(url):
    # Remove postgresql:// prefix
    url = url.replace("postgresql://", "")
    # Split username:password and host:port/dbname
    auth, connection = url.split("@")
    username, password = auth.split(":")
    host_port, dbname = connection.split("/")
    if ":" in host_port:
        host, port = host_port.split(":")
    else:
        host = host_port
        port = "5432"
    return {
        "dbname": dbname,
        "user": username,
        "password": password,
        "host": host,
        "port": port
    }

def get_db_connection():
    """Connect to the PostgreSQL database server."""
    try:
        db_params = parse_db_url(DATABASE_URL)
        conn = psycopg2.connect(**db_params)
        logger.info(f"Connected to database: {db_params['host']}:{db_params['port']}/{db_params['dbname']}")
        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Error connecting to the database: {error}")
        sys.exit(1)

def create_tables():
    """Create necessary tables for storing exercises."""
    conn = None
    try:
        # Connect to the database
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create exercise_categories table if not exists
        cur.execute("""
        CREATE TABLE IF NOT EXISTS exercise_categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """)
        
        # Create exercises table if not exists
        cur.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id UUID PRIMARY KEY,
            category_id INTEGER REFERENCES exercise_categories(id),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            instructions TEXT,
            difficulty VARCHAR(50),
            equipment TEXT,
            form_tips TEXT,
            common_mistakes TEXT,
            muscle_groups JSONB,
            variations TEXT,
            image_url TEXT,
            video_url TEXT,
            created_at TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE,
            category VARCHAR(255)
        )
        """)
        
        # Create index on exercises name
        cur.execute("CREATE INDEX IF NOT EXISTS idx_exercises_name ON exercises(name)")
        
        # Create index on category_id
        cur.execute("CREATE INDEX IF NOT EXISTS idx_exercises_category_id ON exercises(category_id)")
        
        # Commit the transaction
        conn.commit()
        logger.info("Tables created successfully")
        
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Error creating tables: {error}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    logger.info("Creating necessary database tables...")
    create_tables()
    logger.info("Table creation completed.") 