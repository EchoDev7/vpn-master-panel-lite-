import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the parent directory to sys.path to allow importing from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import Base
from app.models.setting import Setting

# Database setup
# Determine absolute path to database relative to this script
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, "vpnmaster_lite.db")

print(f"Connecting to database at: {db_path}")

if not os.path.exists(db_path):
    print(f"WARNING: Database file not found at {db_path}")
    # Fallback check
    if os.path.exists("./vpnmaster_lite.db"):
        db_path = "./vpnmaster_lite.db"
        print(f"Found at relative path: {db_path}")

SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def update_setting(db, key, value):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        print(f"Updating {key}: {setting.value} -> {value}")
        setting.value = value
    else:
        print(f"Creating {key}: {value}")
        new_setting = Setting(key=key, value=value, category="openvpn")
        db.add(new_setting)

def main():
    db = SessionLocal()
    try:
        print("Forcing OpenVPN Settings Update for TCP/443 Scramble...")
        
        updates = {
            "ovpn_protocol": "tcp",
            "ovpn_port": "443",
            "ovpn_tun_mtu": "1420",
            "ovpn_mssfix": "1380",
            "ovpn_compress": "stub-v2",
            "ovpn_redirect_gateway": "1",
            "ovpn_keepalive_interval": "10",
            "ovpn_keepalive_timeout": "60",
        }
        
        for key, val in updates.items():
            update_setting(db, key, val)
            
        db.commit()
        print("✅ Database updated successfully.")
        print("Now run: ./update.sh")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
