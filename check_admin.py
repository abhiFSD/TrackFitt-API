from app.db.database import SessionLocal
from app.models.models import User
from app.api.auth import get_password_hash, verify_password

def check_admin_credentials():
    db = SessionLocal()
    try:
        # Query for admin user
        admin = db.query(User).filter(User.username == "admin").first()
        
        if admin:
            print(f"Admin user found:")
            print(f"Username: {admin.username}")
            print(f"Email: {admin.email}")
            print(f"Is active: {admin.is_active}")
            print(f"Role: {admin.role}")
            
            # Test predefined password
            test_password = "securepassword"
            is_valid = verify_password(test_password, admin.hashed_password)
            print(f"Password 'securepassword' matches: {is_valid}")
            
            # Update password if needed
            if not is_valid:
                print("Updating admin password to 'securepassword'...")
                admin.hashed_password = get_password_hash("securepassword")
                db.commit()
                print("Password updated successfully!")
        else:
            print("No admin user found in database.")
            
    except Exception as e:
        print(f"Error checking admin credentials: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_admin_credentials() 