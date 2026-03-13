from app.db.database import SessionLocal, engine
from app.models.models import User, UserRole, Base
from app.api.auth import get_password_hash
import sys

def create_admin_user(username, email, password):
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"User '{username}' already exists.")
            return
        
        # Create new admin user
        hashed_password = get_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        print(f"Admin user '{username}' created successfully!")
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Default admin credentials
    username = "admin"
    email = "admin@example.com"
    password = "securepassword"
    
    # Use command line arguments if provided
    if len(sys.argv) > 3:
        username = sys.argv[1]
        email = sys.argv[2]
        password = sys.argv[3]
    
    create_admin_user(username, email, password) 