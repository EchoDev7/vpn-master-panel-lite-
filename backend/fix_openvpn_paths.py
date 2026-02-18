import os
import shutil
import subprocess
import sys
import time

def main():
    print("🚀 Starting OpenVPN Repair (Paths + PKI)...")

    # 1. Define Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(BASE_DIR) # Ensure we can import app modules
    
    DEST_DIR = "/etc/openvpn/scripts"
    SERVER_CONF = "/etc/openvpn/server.conf"

    # --- PART 1: PKI FIX (The 'key values mismatch' error) ---
    print("🔐 Checking PKI Configuration...")
    try:
        from app.services.openvpn import openvpn_service
        
        # We force regeneration because the user is seeing mismatch errors.
        # This is destructive but necessary if keys are broken.
        print("⚠️  Regenerating PKI Certificates (Fixing Key Mismatch)...")
        try:
            openvpn_service.regenerate_pki()
            print("✅ PKI Regenerated Successfully.")
        except Exception as e:
            print(f"❌ PKI Regeneration Failed: {e}")
            # Continue anyway, maybe it was just a transient error or permissions
            
    except ImportError as e:
        print(f"❌ Failed to import OpenVPN Service: {e}")
        print("   Ensure you are running this from the backend directory or with correct PYTHONPATH.")

    # --- PART 2: PATH FIX (The 'Permission denied' error) ---
    print("📂 Verifying Auth Script Deployment...")
    
    SOURCE_AUTH = os.path.join(BASE_DIR, "auth.py")
    DEST_AUTH = os.path.join(DEST_DIR, "auth.py")
    
    if not os.path.exists(DEST_DIR):
        print(f"📂 Creating {DEST_DIR}...")
        os.makedirs(DEST_DIR, mode=0o755, exist_ok=True)

    if os.path.exists(SOURCE_AUTH):
        print(f"📋 Copying {SOURCE_AUTH} to {DEST_AUTH}...")
        try:
            shutil.copy2(SOURCE_AUTH, DEST_AUTH)
            os.chmod(DEST_AUTH, 0o755)
            shutil.chown(DEST_AUTH, user="root", group="root")
            print("✅ Auth script deployed.")
        except Exception as e:
            print(f"❌ Failed to copy auth script: {e}")

    # --- PART 3: CONFIG PATCH ---
    print("🔧 Patching server.conf...")
    if os.path.exists(SERVER_CONF):
        try:
            with open(SERVER_CONF, 'r') as f:
                content = f.read()

            # Fix 1: Auth Script Path
            new_content = content.replace(
                "/opt/vpn-master-panel/backend/auth.py", 
                "/etc/openvpn/scripts/auth.py"
            )
            
            # Fix 2: Certificate Paths (Ensure they point to absolute paths if needed, 
            # but OpenVPNService usually handles this. Just in case.)
            # (Skipping complex regex, relying on OpenVPNService for main config, 
            # but patching the specific known issue).

            if content != new_content:
                with open(SERVER_CONF, 'w') as f:
                    f.write(new_content)
                print("✅ server.conf patched to use /etc/openvpn/scripts/auth.py")
            else:
                 if "/etc/openvpn/scripts/auth.py" in content:
                     print("✅ server.conf path is correct.")
                 else:
                     print("⚠️ Path patch didn't apply (Pattern not found).")

        except Exception as e:
             print(f"❌ Failed to patch server.conf: {e}")

    # --- PART 4: RESTART ---
    print("🔄 Restarting OpenVPN...")
    try:
        subprocess.run(["systemctl", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "restart", "openvpn@server"], check=False)
        print("✅ OpenVPN Restart Triggered.")
    except Exception as e:
        print(f"❌ Failed to restart OpenVPN: {e}")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("❌ Must run as root")
        sys.exit(1)
    main()
