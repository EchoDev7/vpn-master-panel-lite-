import os
import shutil
import subprocess
import sys

def main():
    print("🚀 Starting OpenVPN Path Fixer...")

    # 1. Define Paths
    # Adjust source path if running from backend dir or elsewhere
    # We assume this script runs from /opt/vpn-master-panel/backend/
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    REPO_DIR = os.path.dirname(BASE_DIR) # /opt/vpn-master-panel
    
    SOURCE_AUTH = os.path.join(BASE_DIR, "auth.py")
    DEST_DIR = "/etc/openvpn/scripts"
    DEST_AUTH = os.path.join(DEST_DIR, "auth.py")
    SERVER_CONF = "/etc/openvpn/server.conf"

    # 2. Ensure Destination Directory Exists
    if not os.path.exists(DEST_DIR):
        print(f"📂 Creating {DEST_DIR}...")
        os.makedirs(DEST_DIR, mode=0o755, exist_ok=True)

    # 3. Copy Auth Script
    if os.path.exists(SOURCE_AUTH):
        print(f"📋 Copying {SOURCE_AUTH} to {DEST_AUTH}...")
        try:
            shutil.copy2(SOURCE_AUTH, DEST_AUTH)
            os.chmod(DEST_AUTH, 0o755)
            # chown to root:root
            shutil.chown(DEST_AUTH, user="root", group="root")
            print("✅ Auth script deployed successfully.")
        except Exception as e:
            print(f"❌ Failed to copy auth script: {e}")
    else:
        print(f"⚠️ Source auth script not found at {SOURCE_AUTH}. Using whatever is available.")

    # 4. Patch server.conf directly
    if os.path.exists(SERVER_CONF):
        print(f"🔧 Patching {SERVER_CONF}...")
        try:
            with open(SERVER_CONF, 'r') as f:
                content = f.read()

            # Replace old path with new path
            # Also handle potentially other incorrect paths if needed, but this is the main one
            new_content = content.replace(
                "/opt/vpn-master-panel/backend/auth.py", 
                "/etc/openvpn/scripts/auth.py"
            )
            
            # Ensure via-file is present if not
            # (Regex is better but replace is safer for simple string matching)
            
            if content != new_content:
                with open(SERVER_CONF, 'w') as f:
                    f.write(new_content)
                print("✅ server.conf patched to use /etc/openvpn/scripts/auth.py")
            else:
                 print("✅ server.conf already has correct paths (or didn't match old ones).")
                 
        except Exception as e:
             print(f"❌ Failed to patch server.conf: {e}")
    else:
        print(f"❌ {SERVER_CONF} not found. OpenVPN might not be installed.")

    # 5. Restart OpenVPN
    print("🔄 Restarting OpenVPN...")
    try:
        subprocess.run(["systemctl", "daemon-reload"], check=False)
        # Try specific service first
        if subprocess.run(["systemctl", "is-active", "openvpn@server"], capture_output=True).returncode == 0:
             subprocess.run(["systemctl", "restart", "openvpn@server"], check=False)
        else:
             subprocess.run(["systemctl", "restart", "openvpn"], check=False)
             
        # Also ensure apparmor reload
        if os.path.exists("/etc/apparmor.d/usr.sbin.openvpn"):
             subprocess.run(["systemctl", "reload", "apparmor"], check=False)
             
        print("✅ OpenVPN Restart Triggered.")
    except Exception as e:
        print(f"❌ Failed to restart OpenVPN: {e}")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("❌ Must run as root")
        sys.exit(1)
    main()
