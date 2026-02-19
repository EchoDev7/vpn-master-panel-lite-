import sqlite3
import os

db_files = [f for f in os.listdir('.') if f.endswith('.db')]
print(f"Found .db files in current directory: {db_files}")

target_db = "vpnmaster_lite.db"
if target_db not in db_files and "app.db" in db_files:
    target_db = "app.db"
    
print(f"Connecting to: {target_db}")

try:
    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables found:")
    for t in tables:
        print(f" - {t[0]}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
