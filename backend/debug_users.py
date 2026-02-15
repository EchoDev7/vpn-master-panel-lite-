import sys
import os
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.api.users import UserResponse
from pydantic import ValidationError

def debug_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Found {len(users)} users in database.")
        
        for user in users:
            print(f"\n--- Checking User: {user.username} (ID: {user.id}) ---")
            
            # 1. Check raw database values
            print("Raw values:")
            print(f"  role: {user.role} ({type(user.role)})")
            print(f"  status: {user.status} ({type(user.status)})")
            print(f"  data_limit_gb: {user.data_limit_gb}")
            print(f"  data_usage_gb (prop): {user.data_usage_gb}")
            print(f"  expiry_date: {user.expiry_date}")
            print(f"  created_at: {user.created_at}")
            
            # 2. Try to validate with Pydantic
            try:
                pydantic_user = UserResponse.model_validate(user)
                print("✅ Pydantic Validation Passed")
            except ValidationError as e:
                print("❌ Pydantic Validation FAILED!")
                print(e)
            except Exception as e:
                print(f"❌ Unexpected Error during validation: {e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"Global Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_users()
