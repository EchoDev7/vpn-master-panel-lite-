
import sqlite3
import os

DB_PATH = os.path.join("backend", "vpnmaster_lite.db")

print(f"Connecting to database: {DB_PATH}")

if not os.path.exists(DB_PATH):
    print(f"❌ Database not found at {DB_PATH}")
    if os.path.exists("vpnmaster_lite.db"):
        DB_PATH = "vpnmaster_lite.db"
    else:
        exit(1)

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check current value
    cursor.execute("SELECT value FROM settings WHERE key='ovpn_server_ip'")
    row = cursor.fetchone()
    current = row[0] if row else "NOT SET"
    print(f"Current 'ovpn_server_ip': {current}")
    
    # Update to 89.167.0.72
    TARGET_IP = "89.167.0.72"
    print(f"Updating 'ovpn_server_ip' to '{TARGET_IP}'...")
    
    cursor.execute(f"UPDATE settings SET value='{TARGET_IP}' WHERE key='ovpn_server_ip'")
    conn.commit()
    
    # Verify
    cursor.execute("SELECT value FROM settings WHERE key='ovpn_server_ip'")
    new_val = cursor.fetchone()[0]
    print(f"✅ New 'ovpn_server_ip': {new_val}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
