import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment or use default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/workout_db")

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

# Run migration
def run_migration():
    print("Starting migration...")
    try:
        # Parse the database URL
        db_params = parse_db_url(DATABASE_URL)
        print(f"Connecting to database: {db_params['host']}:{db_params['port']}/{db_params['dbname']}")
        
        # Connect to the database
        conn = psycopg2.connect(**db_params)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create exercise_categories table
        print("Creating exercise_categories table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exercise_categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        # Check if the constraint already exists
        print("Checking for existing constraint...")
        cursor.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE constraint_name = 'fk_exercise_category'
        """)
        constraint_exists = cursor.fetchone() is not None
        
        # Add category_id column to exercises table
        print("Adding category_id column to exercises table...")
        cursor.execute("""
            ALTER TABLE exercises 
            ADD COLUMN IF NOT EXISTS category_id INTEGER
        """)
        
        # Add foreign key constraint if it doesn't exist
        if not constraint_exists:
            print("Adding foreign key constraint...")
            cursor.execute("""
                ALTER TABLE exercises
                ADD CONSTRAINT fk_exercise_category
                FOREIGN KEY (category_id) 
                REFERENCES exercise_categories(id)
            """)
        
        # Get existing distinct categories from exercises
        print("Migrating existing categories...")
        cursor.execute("""
            SELECT DISTINCT category FROM exercises 
            WHERE category IS NOT NULL AND category != ''
        """)
        categories = cursor.fetchall()
        print(f"Found {len(categories)} distinct categories")
        
        # Insert distinct categories into the exercise_categories table
        for category_tuple in categories:
            category_name = category_tuple[0]
            if category_name:
                print(f"Adding category: {category_name}")
                cursor.execute("""
                    INSERT INTO exercise_categories (name) 
                    VALUES (%s) 
                    ON CONFLICT (name) DO NOTHING
                """, (category_name,))
        
        # Update exercises to set category_id based on category name
        print("Updating exercises with category_id...")
        cursor.execute("""
            UPDATE exercises e
            SET category_id = ec.id
            FROM exercise_categories ec
            WHERE e.category = ec.name
        """)
        
        # Close the connection
        cursor.close()
        conn.close()
        
        print("Migration completed successfully!")
        return True
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    run_migration() 