import sys
import os
import sqlite3
from datetime import datetime

# Colors for output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
NC = '\033[0m'

DB_PATH = "vpnmaster_lite.db"

def print_status(message, status="ok"):
    if status == "ok":
        print(f"  [{GREEN}OK{NC}] {message}")
    elif status == "warn":
        print(f"  [{YELLOW}WARN{NC}] {message}")
    else:
        print(f"  [{RED}FAIL{NC}] {message}")

def check_database():
    print(f"\n{YELLOW}🗄️  Deep Database Diagnostics{NC}")
    print("--------------------------------------------------------")
    
    # 1. File Existence
    if not os.path.exists(DB_PATH):
        print_status(f"Database file not found: {DB_PATH}", "fail")
        return
    
    file_size = os.path.getsize(DB_PATH) / 1024 # KB
    print_status(f"Database file exists ({file_size:.2f} KB)", "ok")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 2. Integrity Check
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()[0]
        if result == "ok":
            print_status("Structure Integrity Check Passed", "ok")
        else:
            print_status(f"Structure Integrity Failed: {result}", "fail")
            
        # 3. Foreign Key Check
        cursor.execute("PRAGMA foreign_key_check;")
        fk_errors = cursor.fetchall()
        if not fk_errors:
             print_status("Foreign Key Constraints Valid", "ok")
        else:
             print_status(f"Foreign Key Errors Found: {len(fk_errors)}", "warn")

        # 4. Table Verification
        tables = ["users", "settings", "vpn_servers", "traffic_logs"]
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [t for t in tables if t not in existing_tables]
        if missing_tables:
            print_status(f"Missing Core Tables: {', '.join(missing_tables)}", "fail")
        else:
            print_status(f"All Core Tables Present ({len(existing_tables)} total)", "ok")
            
        # 5. Critical Data Check
        # Check Admin User (Super Admin or Admin)
        cursor.execute("SELECT username, status FROM users WHERE role='super_admin' OR role='admin' LIMIT 1")
        admin = cursor.fetchone()
        if admin:
            # status is an Enum in python, but string in sqlite usually
            print_status(f"Admin User Found: {admin[0]} (Status: {admin[1]})", "ok")
        else:
            print_status("No Admin User Found!", "fail")
            
        # Check Settings
        cursor.execute("SELECT count(*) FROM settings")
        settings_count = cursor.fetchone()[0]
        print_status(f"Configuration Entries: {settings_count}", "ok")
        
        conn.close()
        
    except sqlite3.Error as e:
        print_status(f"Database Connection Error: {e}", "fail")
    except Exception as e:
        print_status(f"Unexpected Error: {e}", "fail")

if __name__ == "__main__":
    check_database()
