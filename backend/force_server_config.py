
import os
import sys
import subprocess
from app.services.openvpn import OpenVPNService

def run_command(command: str):
    """Running command with logging"""
    print(f"🚀 Running: {command}")
    try:
        subprocess.check_call(command, shell=True)
        print("✅ Success")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")

def main():
    if os.geteuid() != 0:
        print("❌ This script must be run as root!")
        sys.exit(1)

    print("🔧 Generating OpenVPN Server Config...")
    try:
        service = OpenVPNService()
        config_content = service.generate_server_config()
        
        config_path = "/etc/openvpn/server.conf"
        with open(config_path, "w") as f:
            f.write(config_content)
        
        print(f"✅ Config written to {config_path}")
        print("📝 Content Preview:")
        print("--------------------------------")
        print("\n".join(config_content.splitlines()[:5]))
        print("... (truncated)")
        print("--------------------------------")

        print("🔄 Restarting OpenVPN Service...")
        # Try both service names
        if subprocess.call("systemctl list-units --full -all | grep -q openvpn@server.service", shell=True) == 0:
            run_command("systemctl restart openvpn@server")
        else:
            run_command("systemctl restart openvpn")

        print("✅ Done! OpenVPN should now be listening on port 443 (if configured).")

    except Exception as e:
        print(f"❌ Critical Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
