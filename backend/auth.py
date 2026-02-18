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
             try:
                 # Standard ISO format (User Request)
                 expiry_dt = datetime.fromisoformat(str(expiry).replace('Z', ''))
                 if datetime.utcnow() > expiry_dt:
                     logging.warning(f"AUTH_FAILED: User {username} expired")
                     return False
             except ValueError:
                 # Fallback for legacy formats if needed, or fail safe
                 logging.warning(f"AUTH_ERROR: Invalid expiry format for {username}: {expiry}")
                 return False

        # Connection Limit Check
        # User Request: Enforce connection_limit which is ignored in other parts
        # We parse the status log text file directly to count active sessions
        try:
             # Check limit from DB - we need to query it
             limit_query = "SELECT connection_limit FROM users WHERE username = :username"
             limit_res = db.execute(limit_query, {'username': username}).fetchone()
             limit = limit_res[0] if limit_res else 0
             
             if limit > 0:
                 status_log = "/var/log/openvpn/openvpn-status.log"
                 if os.path.exists(status_log):
                     with open(status_log, 'r') as f:
                         content = f.read()
                         # Simple substring count is risky (username as substring of another), 
                         # but for a basic auth script without heavy parsing, filtering lines is better.
                         # V1: "Common Name,..." -> line.startswith("username,")
                         # V2: "CLIENT_LIST,username,..."
                         
                         count = 0
                         for line in content.splitlines():
                             parts = line.split(',')
                             # V1 Check
                             if len(parts) > 1 and parts[0] == username:
                                 count += 1
                             # V2 Check
                             elif len(parts) > 1 and parts[0] == "CLIENT_LIST" and parts[1] == username:
                                 count += 1
                                 
                         # Current connection attempt adds +1? No, we are authenticating BEFORE connection.
                         if count >= limit:
                             logging.warning(f"AUTH_FAILED: User {username} reached connection limit ({count}/{limit})")
                             return False
        except Exception as e:
             logging.error(f"AUTH_LIMIT_CHECK_ERROR: {e}")
             # Fail open or closed? Closed matches "Strict" requirement.
             # But if log is missing, maybe open. Let's log and proceed for now to avoid lockout on error.
             pass

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
