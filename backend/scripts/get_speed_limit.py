#!/usr/bin/python3
import sys
import sqlite3
import os

username = sys.argv[1] if len(sys.argv) > 1 else ""
# Ensure we use correct DB path
DB_PATH = "/opt/vpn-master-panel/backend/vpnmaster_lite.db"
if not os.path.exists(DB_PATH):
    # Fallback to relative if testing
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'vpnmaster_lite.db')

try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Check if column exists first (safeguard)
    try:
        cur.execute("SELECT speed_limit_mbps FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        if row and row[0]:
            print(int(row[0]))
        else:
            print(0)
    except:
        print(0)
    conn.close()
except:
    print(0)
