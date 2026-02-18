import sqlite3
import secrets
import os

DB_PATH = "vpnmaster_lite.db"

def debug_and_fix():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Debug: Print all users
        cursor.execute("SELECT id, username, subscription_token FROM users")
        all_users = cursor.fetchall()
        print(f"Total users in DB: {len(all_users)}")
        for u in all_users:
            token_display = u[2] if u[2] else "NULL"
            print(f"User: {u[1]} (ID: {u[0]}), Token: {token_display}")

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

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    debug_and_fix()
