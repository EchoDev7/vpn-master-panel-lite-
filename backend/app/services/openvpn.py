"""
OpenVPN Service - Generate client configurations
"""
import os
import logging
from typing import Optional

# Setup logging
logger = logging.getLogger(__name__)

class OpenVPNService:
    """OpenVPN Configuration Generator"""
    
    # Standard paths for OpenVPN (Debian/Ubuntu)
    CA_PATH = "/etc/openvpn/server/ca.crt"
    TA_PATH = "/etc/openvpn/server/ta.key"
    
    def __init__(self):
        self.server_ip = self._get_public_ip()
        
    def _get_public_ip(self) -> str:
        """Get server public IP (naive implementation, should use config)"""
        # In a real scenario, this should come from settings or external check
        # For now, we rely on the caller to provide it or fallback to a placeholder
        return "YOUR_SERVER_IP" 

    def _read_file(self, path: str) -> str:
        """Read file content safely"""
        if not os.path.exists(path):
            logger.warning(f"File not found: {path}")
            return f"# MISSING: {path}"
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to read {path}: {e}")
            return f"# ERROR READING: {path}"

    def _ensure_pki(self):
        """Ensure PKI (CA/Cert/Key) exists, generate if missing"""
        if os.path.exists(self.CA_PATH) and os.path.exists(self.TA_PATH):
            return

        logger.info("Generating OpenVPN PKI (Self-Signed)...")
        try:
            import subprocess
            
            # Create directory
            os.makedirs(os.path.dirname(self.CA_PATH), exist_ok=True)
            
            # 1. Generate CA
            subprocess.run(
                f"openssl req -new -x509 -days 3650 -nodes -text -out {self.CA_PATH} -keyout {self.CA_PATH} -subj '/CN=VPN-Master-CA'",
                shell=True, check=True
            )
            
            # 2. Generate TA key
            subprocess.run(
                f"openvpn --genkey secret {self.TA_PATH}",
                shell=True, check=True
            )
            
            logger.info("✅ OpenVPN PKI generated successfully")
        except Exception as e:
            logger.error(f"❌ Failed to generate PKI: {e}")

    def generate_client_config(
        self, 
        username: str, 
        password: str = None, 
        server_ip: str = None, 
        port: int = 1194, 
        protocol: str = "udp"
    ) -> str:
        """
        Generate .ovpn content
        """
        # Ensure certificates exist
        self._ensure_pki()
        
        if not server_ip:
            # Fallback to determining IP, or use a placeholder
            try:
                import requests
                server_ip = requests.get('https://api.ipify.org', timeout=2).text
            except:
                server_ip = "YOUR_SERVER_IP"

        # Read Core Certificates
        ca_cert = self._read_file(self.CA_PATH)
        tls_auth = self._read_file(self.TA_PATH)
        
        # Fetch settings from DB
        from ..database import get_db_context
        from ..models.setting import Setting
        
        # Default Settings (Modern OpenVPN 2.4+)
        settings_map = {
            "protocol": "udp",
            "port": "1194",
            "scramble": "0",
            "mtu": "1500",
            "data_ciphers": "AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305",
            "tls_ciphers": "TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384:TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384",
            "auth_digest": "SHA256",
            "tls_version_min": "1.2",
            "compression": "none" # lz4-v2, comp-lzo
        }
        
        with get_db_context() as db:
            all_settings = db.query(Setting).all()
            for s in all_settings:
                if s.key.startswith("ovpn_"):
                    key = s.key.replace("ovpn_", "")
                    if key in settings_map:
                        settings_map[key] = s.value

            # Override server_ip if set in settings
            s_ip = db.query(Setting).filter(Setting.key == "wg_endpoint_ip").first() # Reuse endpoint ip setting
            if s_ip and s_ip.value: server_ip = s_ip.value

        # Determine protocol
        final_protocol = protocol if protocol else ("udp" if settings_map["protocol"] == "both" else settings_map["protocol"])
        
        # Adjust port logic if needed (e.g. separate ports for tcp/udp)
        final_port = settings_map["port"] # simplified for now

        # Base Configuration Template (OpenVPN 2.4/2.5/2.6 Compatible)
        config = f"""client
dev tun
proto {final_protocol}
remote {server_ip} {final_port}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server

# Modern Security Settings
auth {settings_map["auth_digest"]}
data-ciphers {settings_map["data_ciphers"]}
data-ciphers-fallback AES-256-GCM
tls-version-min {settings_map["tls_version_min"]}
tls-client

# Compression
"""
        if settings_map["compression"] != "none":
             config += f"compress {settings_map['compression']}\n"
        
        config += f"""
# Anti-Censorship & Optimization
ignore-unknown-option block-outside-dns
block-outside-dns
verb 3
key-direction 1
tun-mtu {settings_map['mtu']}
mssfix {int(settings_map['mtu']) - 40}

# Custom Configuration (from Admin Panel)
{settings_map['custom_config']}
"""

        # Add Scramble/Obfuscation
        if settings_map["scramble"] == "1":
            config += """
scramble obfuscate "vpnmaster"
"""

        # User Credentials (User/Pass Auth Only - No Client Certs)
        config += """
# User Credentials
auth-user-pass

<ca>
{ca_cert}
</ca>
"""

        # Add TLS Auth if available
        if "BEGIN OpenVPN Static key" in tls_auth:
            config += f"""
<tls-auth>
{tls_auth}
</tls-auth>
"""
        
        return config

    def regenerate_pki(self):
        """Regenerate CA and Server Certificates"""
        logger.info("Regenerating OpenVPN PKI...")
        try:
            import subprocess
            import shutil
            
            # Ensure parent data directory exists
            os.makedirs(self.DATA_DIR, exist_ok=True)

            # Backup existing
            if os.path.exists(self.CA_PATH):
                shutil.copy(self.CA_PATH, f"{self.CA_PATH}.bak")
            
            # 1. Generate CA
            subprocess.run(
                f"openssl req -new -x509 -days 3650 -nodes -text -out {self.CA_PATH} -keyout {self.CA_PATH} -subj '/CN=VPN-Master-Root-CA'",
                shell=True, check=True
            )
            
            # 2. Generate TLS Auth Key (ta.key)
            subprocess.run(
                f"openvpn --genkey secret {self.TA_PATH}",
                shell=True, check=True
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to regenerate PKI: {e}")
            raise e

# Singleton instance
openvpn_service = OpenVPNService()
