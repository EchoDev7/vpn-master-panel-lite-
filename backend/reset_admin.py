from app.database import SessionLocal
from app.models.user import User
from app.utils.security import get_password_hash
import sys

def reset_password(username, new_password):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"❌ User '{username}' not found!")
            return
            
        print(f"User found: {user.username} (Role: {user.role})")
        
        # Update password
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        
        print(f"✅ Password for '{username}' has been successfully reset!")
        print(f"👉 New Password: {new_password}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python reset_admin.py <username> <new_password>")
        print("Example: python reset_admin.py admin 123456")
    else:
        reset_password(sys.argv[1], sys.argv[2])
