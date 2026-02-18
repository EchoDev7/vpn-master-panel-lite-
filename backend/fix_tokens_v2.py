import sqlite3
import secrets
import os

DB_PATH = "vpnmaster_lite.db"

def fix_tokens():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check for users with null token
        cursor.execute("SELECT id, username FROM users WHERE subscription_token IS NULL")
        users = cursor.fetchall()
        print(f"Found {len(users)} users without subscription token.")

        count = 0
        for user_id, username in users:
            token = secrets.token_urlsafe(16)
            cursor.execute("UPDATE users SET subscription_token = ? WHERE id = ?", (token, user_id))
            print(f"Generated token for user: {username}")
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
    fix_tokens()
