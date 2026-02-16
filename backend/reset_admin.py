import sys
import os

# Add current directory to path so we can import app modules
sys.path.append(os.getcwd())

from app.database import SessionLocal, init_db
from app.models.user import User, UserRole
from app.utils.security import get_password_hash

def reset_password():
    print("🔄 Connecting to database...")
    db = SessionLocal()
    
    try:
        # Ensure tables exist
        init_db()
        
        username = "admin"
        password = "admin"
        
        # Check if user exists
        user = db.query(User).filter(User.username == username).first()
        
        if user:
            print(f"👤 User '{username}' found. Updating password...")
            user.hashed_password = get_password_hash(password)
            user.is_active = True
            user.role = UserRole.SUPER_ADMIN
            db.commit()
            print(f"✅ SUCCESS: Password for '{username}' has been reset to '{password}'")
        else:
            print(f"👤 User '{username}' not found. Creating new admin...")
            new_admin = User(
                username=username,
                email="admin@vpnmaster.local",
                hashed_password=get_password_hash(password),
                role=UserRole.SUPER_ADMIN,
                full_name="Super Admin",
                is_active=True
            )
            db.add(new_admin)
            db.commit()
            print(f"✅ SUCCESS: Created new user '{username}' with password '{password}'")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_password()
