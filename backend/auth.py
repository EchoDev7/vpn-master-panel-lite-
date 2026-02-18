#!/usr/bin/python3
import sys
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Configure logging
logging.basicConfig(filename='/var/log/openvpn/auth.log', level=logging.INFO, format='%(asctime)s %(message)s')

# Database Setup
DB_PATH = "/opt/vpn-master-panel/backend/vpnmaster_lite.db"
# Fallback for dev environment
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'vpnmaster_lite.db')

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def auth_user(username, password):
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Raw SQL to avoid model dependency issues in standalone script
        # Check active users who are not expired
        query = "SELECT hashed_password, status, expiry_date FROM users WHERE username = :username"
        result = db.execute(query, {'username': username}).fetchone()
        
        if not result:
            logging.warning(f"AUTH_FAILED: User {username} not found")
            return False
            
        hashed_pw, status, expiry = result
        
        if status != "active":
            logging.warning(f"AUTH_FAILED: User {username} is {status}")
            return False
            
        if expiry:
             from datetime import datetime
             # Handle various date formats from SQLite
             exp_dt = None
             if isinstance(expiry, str):
                 for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                     try:
                         exp_dt = datetime.strptime(expiry, fmt)
                         break
                     except ValueError:
                         continue
             else:
                 exp_dt = expiry

             if exp_dt and exp_dt < datetime.utcnow():
                 logging.warning(f"AUTH_FAILED: User {username} expired at {exp_dt}")
                 return False

        if verify_password(password, hashed_pw):
            logging.info(f"AUTH_SUCCESS: User {username}")
            return True
        else:
            logging.warning(f"AUTH_FAILED: User {username} wrong password")
            return False
            
    except Exception as e:
        logging.error(f"AUTH_ERROR: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    # OpenVPN passes credentials via file
    if len(sys.argv) < 2:
        logging.error("Missing password file argument")
        sys.exit(1)
        
    pass_file = sys.argv[1]
    
    try:
        with open(pass_file, 'r') as f:
            username = f.readline().strip()
            password = f.readline().strip()
            
        if auth_user(username, password):
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        logging.error(f"File Error: {e}")
        sys.exit(1)
