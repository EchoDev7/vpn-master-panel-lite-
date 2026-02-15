from app.database import SessionLocal
from app.models.user import User
from app.config import settings

def check_admin():
    db = SessionLocal()
    try:
        # Check by default username
        username = settings.INITIAL_ADMIN_USERNAME
        user = db.query(User).filter(User.username == username).first()
        
        if user:
            print(f"✅ User found: {user.username}")
            print(f"Role: {user.role}")
            print(f"Is Active: {user.is_active}")
            print(f"Super Admin: {user.role == 'super_admin'}")
        else:
            print(f"❌ User {username} not found!")
            
            # List all users
            users = db.query(User).all()
            print("\nAll users:")
            for u in users:
                print(f"- {u.username}: {u.role}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_admin()
