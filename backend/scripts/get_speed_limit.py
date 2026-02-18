#!/usr/bin/python3
import sys
import sqlite3
import os

# F7: Helper for bandwidth shaping
# Fetches speed limit in Mbps for a given username

username = sys.argv[1] if len(sys.argv) > 1 else ""
DB_PATH = "/opt/vpn-master-panel/backend/vpnmaster_lite.db"

# Fallback path for dev/test
if not os.path.exists(DB_PATH):
    # Try relative path
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend", "vpnmaster_lite.db")

try:
    if not os.path.exists(DB_PATH):
        print(0)
        sys.exit(0)
        
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Speed limit is in Mbps
    cur.execute("SELECT speed_limit_mbps FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    
    if row and row[0]:
        print(int(row[0]))
    else:
        print(0)
except:
    print(0)
