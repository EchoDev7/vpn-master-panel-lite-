from app.database import SessionLocal
from app.models.user import User

def fix_database_values():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        fixed_count = 0
        
        print(f"Checking {len(users)} users for NULL values...")
        
        for user in users:
            changed = False
            
            if user.data_limit_gb is None:
                print(f"User {user.username}: Fixing data_limit_gb (None -> 0)")
                user.data_limit_gb = 0
                changed = True
                
            if user.total_upload_bytes is None:
                print(f"User {user.username}: Fixing total_upload_bytes (None -> 0)")
                user.total_upload_bytes = 0
                changed = True
                
            if user.total_download_bytes is None:
                print(f"User {user.username}: Fixing total_download_bytes (None -> 0)")
                user.total_download_bytes = 0
                changed = True
                
            if changed:
                fixed_count += 1
        
        if fixed_count > 0:
            db.commit()
            print(f"✅ Successfully fixed values for {fixed_count} users.")
        else:
            print("✅ No users needed fixing.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_database_values()
