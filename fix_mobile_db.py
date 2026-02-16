
import sqlite3
import os

DB_PATH = os.path.join("backend", "vpnmaster_lite.db")

print(f"Connecting to database: {DB_PATH}")

if not os.path.exists(DB_PATH):
    print(f"❌ Database not found at {DB_PATH}")
    # Try current directory if running from backend
    if os.path.exists("vpnmaster_lite.db"):
        DB_PATH = "vpnmaster_lite.db"
        print(f"Found localized DB: {DB_PATH}")
    else:
        exit(1)

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check current value
    cursor.execute("SELECT value FROM settings WHERE key='ovpn_block_outside_dns'")
    row = cursor.fetchone()
    current = row[0] if row else "NOT FOUND"
    print(f"Current 'ovpn_block_outside_dns': {current}")
    
    # Update to 0
    print("Updating 'ovpn_block_outside_dns' to '0'...")
    cursor.execute("INSERT OR REPLACE INTO settings (key, value, category, description) VALUES ('ovpn_block_outside_dns', '0', 'openvpn', 'Prevent DNS leaks on Windows (Disabled for Mobile)')")
    conn.commit()
    
    # Verify
    cursor.execute("SELECT value FROM settings WHERE key='ovpn_block_outside_dns'")
    new_val = cursor.fetchone()[0]
    print(f"✅ New 'ovpn_block_outside_dns': {new_val}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
