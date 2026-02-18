import sqlite3
import secrets
import os

DB_PATHS = ["vpnmaster_lite.db", "../vpnmaster_lite.db"]

def debug_and_fix():
    for db_path in DB_PATHS:
        if not os.path.exists(db_path):
            print(f"Database not found at {db_path}")
            continue
            
        print(f"\nScanning database: {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Debug: Print all users
            cursor.execute("SELECT id, username, subscription_token FROM users")
            all_users = cursor.fetchall()
            print(f"Total users in DB: {len(all_users)}")
            
            # Fix Logic: NULL or Empty String
            cursor.execute("SELECT id, username FROM users WHERE subscription_token IS NULL OR subscription_token = ''")
            target_users = cursor.fetchall()
            print(f"Users needing fix: {len(target_users)}")

            count = 0
            for user_id, username in target_users:
                token = secrets.token_urlsafe(16)
                cursor.execute("UPDATE users SET subscription_token = ? WHERE id = ?", (token, user_id))
                print(f"Generated token for user: {username} -> {token}")
                count += 1
            
            if count > 0:
                conn.commit()
                print(f"Successfully updated {count} users.")
            else:
                print("No users needed updating.")
                
            conn.close()

        except Exception as e:
            print(f"Error processing {db_path}: {e}")

if __name__ == "__main__":
    debug_and_fix()
