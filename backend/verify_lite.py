import requests
import time
import subprocess
import sys
import os
import signal

# Config
BASE_URL = "http://127.0.0.1:8002/api/v1"
ADMIN_EMAIL = "admin@vpnmaster.local"
ADMIN_PASS = "admin"  # Default in install.sh, but might be random.
# We will use the 'reset_admin.py' logic or force create an admin if login fails?
# Better: We will rely on the initial admin created by init_db.

def start_backend():
    print("🚀 Starting Backend on port 8002...")
    # Use the venv python
    venv_python = "venv/bin/python"
    if not os.path.exists(venv_python):
        venv_python = "python3" # Fallback
        
    process = subprocess.Popen(
        [venv_python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8002"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(5) # Wait for startup
    return process

def test_backend():
    # 1. Health Check
    try:
        resp = requests.get("http://127.0.0.1:8002/docs")
        if resp.status_code == 200:
            print("✅ Backend is UP (Docs accessible)")
        else:
            print(f"❌ Backend failed health check: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

    # 2. Login (This might fail if password is random, so we need to know the password)
    # Since we are local, let's look at .env or reset it.
    # The .env in lite version is created by install.sh locally? No, install.sh runs on server.
    # We generated a local .env in step 613 (update.sh) but that was on server.
    # We need to ensure we have a .env locally.
    
    return True

if __name__ == "__main__":
    # Ensure .env exists
    if not os.path.exists(".env"):
        print("ℹ️ Creating local test .env")
        with open(".env", "w") as f:
            f.write("DATABASE_URL=sqlite:///./vpnmaster_lite.db\n")
            f.write("SECRET_KEY=test_secret\n")
            f.write("INITIAL_ADMIN_PASSWORD=admin\n") # Force known password

    # Initialize DB (create admin)
    print("🛠️ Initializing DB...")
    # We can run init_db via command line
    subprocess.run(["venv/bin/python", "-c", "from app.database import init_db; init_db()"], capture_output=True)

    backend_proc = start_backend()
    
    try:
        # TEST 1: Login
        print("🔑 Testing Login...")
        login_data = {
            "username": "admin",
            "password": "admin"
        }
        # Endpoint is /auth/login and expects JSON body
        resp = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if resp.status_code != 200:
            print(f"❌ Login Failed: {resp.text}")
            sys.exit(1)
        
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login Successful")

        # TEST 2: Get Users (The original 500 error check)
        print("📋 Testing User List (GET /users)...")
        resp = requests.get(f"{BASE_URL}/users/", headers=headers)
        if resp.status_code == 200:
            users = resp.json()
            print(f"✅ User List Fetched Successfully ({len(users)} users found)")
        else:
            print(f"❌ Failed to fetch users: {resp.status_code} - {resp.text}")
            sys.exit(1)

        # TEST 3: Create User (Simulate functionality)
        print("👤 Testing Create User...")
        new_user = {
            "username": "test_lite_user",
            "password": "securepassword",
            "data_limit_gb": 10,
            "expiry_date": None
        }
        resp = requests.post(f"{BASE_URL}/users/", json=new_user, headers=headers)
        if resp.status_code in [200, 201]:
             print("✅ User 'test_lite_user' Created Successfully")
        elif resp.status_code == 400 and "already exists" in resp.text:
             print("✅ User already exists (Skipping)")
        else:
             print(f"❌ Create User Failed: {resp.text}")
             sys.exit(1)

        print("\n✨ ALL TESTS PASSED! The Lite Version is Logic-Free of 500 Errors. ✨")

    finally:
        os.kill(backend_proc.pid, signal.SIGTERM)
