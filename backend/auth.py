#!/usr/bin/python3
import sys
import os
import logging
from sqlalchemy import create_engine, text
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
    # F9: Brute-Force Detection - Log IP
    client_ip = os.environ.get("untrusted_ip", "unknown")
    
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Raw SQL to avoid model dependency issues in standalone script
        # Check active users who are not expired
        query = text("SELECT hashed_password, status, expiry_date FROM users WHERE username = :username")
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

        # Connection Limit Check (F3 - User Requested via Management Socket)
        try:
             # Check limit from DB
             limit_query = text("SELECT connection_limit FROM users WHERE username = :username")
             limit_res = db.execute(limit_query, {'username': username}).fetchone()
             limit = limit_res[0] if limit_res else 0
             
             if limit > 0:
                 # Helper to Get Active Connections via Socket (Inline to keep auth.py standalone)
                 import socket
                 def count_active_sessions(target_user):
                     try:
                         with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                             s.settimeout(2)
                             s.connect(('127.0.0.1', 7505))
                             s.recv(1024) # banner
                             s.sendall(b'status 2\n')
                             resp = b''
                             while True:
                                 chunk = s.recv(4096)
                                 if not chunk: break
                                 resp += chunk
                                 if b'END' in resp or b'ERROR' in resp: break
                             s.sendall(b'quit\n')
                             
                             # Parse
                             count = 0
                             for line in resp.decode(errors='ignore').splitlines():
                                 if line.startswith('CLIENT_LIST,') and 'Common Name' not in line:
                                     parts = line.split(',')
                                     # parts[1] is username
                                     if len(parts) > 1 and parts[1] == target_user:
                                         count += 1
                             return count
                     except:
                         return 0 # Fail open if mgmt socket down
                 
                 active_count = count_active_sessions(username)
                 # Current attempt is NOT yet in the list (auth phase happens before)
                 if active_count >= limit:
                     logging.warning(f"AUTH_FAILED: User {username} connection limit exceeded ({active_count}/{limit})")
                     return False

        except Exception as e:
             logging.error(f"AUTH_LIMIT_CHECK_ERROR: {e}")
             pass

        if verify_password(password, hashed_pw):
            logging.info(f"AUTH_SUCCESS: User {username} from {client_ip}")
            return True
        else:
            logging.warning(f"AUTH_FAILED: User {username} from {client_ip} wrong password")
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
