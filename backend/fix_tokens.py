import sys
import os
import secrets
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.user import User

def fix_tokens():
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.subscription_token == None).all()
        print(f"Found {len(users)} users without subscription token.")
        
        count = 0
        for user in users:
            token = secrets.token_urlsafe(16)
            user.subscription_token = token
            print(f"Generated token for user: {user.username}")
            count += 1
            
        if count > 0:
            db.commit()
            print(f"Successfully updated {count} users.")
        else:
            print("No users needed updating.")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_tokens()
