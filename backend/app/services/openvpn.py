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
    
    # Paths for OpenVPN PKI (Local storage to avoid permission issues)
    # Using specific directory within the project
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, "data", "openvpn")
    CA_PATH = os.path.join(DATA_DIR, "ca.crt")
    CA_KEY_PATH = os.path.join(DATA_DIR, "ca.key")
    TA_PATH = os.path.join(DATA_DIR, "ta.key")
    
    def __init__(self):
        self.server_ip = self._get_public_ip()
        
    def _get_public_ip(self) -> str:
        """Get server public IP with multiple fallbacks"""
        import socket
        try:
            import requests
            # Try primary provider
            try:
                return requests.get('https://api.ipify.org', timeout=3).text.strip()
            except:
                pass
            
            # Try secondary provider
            try:
                return requests.get('https://checkip.amazonaws.com', timeout=3).text.strip()
            except:
                pass

            # Fallback to local socket (best guess for private IP/NAT)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
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
        """Ensure PKI (CA/Cert/Key) exists"""
        if os.path.exists(self.CA_PATH) and os.path.exists(self.TA_PATH):
            return

        # If missing, try to generate
        try:
            self.regenerate_pki()
        except Exception as e:
            logger.error(f"Auto-generation of PKI failed: {e}")

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
        self._ensure_pki()
        
        # Read Certs (Only CA Cert, NOT Key)
        ca_cert = self._read_file(self.CA_PATH)
        tls_auth = self._read_file(self.TA_PATH)
        
        # Fetch settings from DB
        from ..database import get_db_context
        from ..models.setting import Setting
        
        settings_map = {
            "protocol": "udp",
            "port": "1194",
            "scramble": "0",
            "mtu": "1500",
            "data_ciphers": "AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305",
            "data_ciphers_fallback": "AES-256-GCM",
            "tls_ciphers": "TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384:TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384",
            "auth_digest": "SHA256",
            "tls_version_min": "1.2",
            "compression": "none",
            "dns": "8.8.8.8,1.1.1.1",
            # New Advanced Settings
            "topology": "subnet",
            "redirect_gateway": "1", # 1=enable, 0=disable
            "verb": "3",
            "float": "1",
            "keepalive_interval": "10",
            "keepalive_timeout": "60",
            "custom_config": ""
        }
        
        with get_db_context() as db:
            all_settings = db.query(Setting).all()
            for s in all_settings:
                if s.key.startswith("ovpn_"):
                    key = s.key.replace("ovpn_", "")
                    if key in settings_map:
                        settings_map[key] = s.value

            # Determine Server IP
            # 1. Check override setting 'wg_endpoint_ip' (or a specific ovpn ip if we had one)
            s_ip = db.query(Setting).filter(Setting.key == "wg_endpoint_ip").first()
            if s_ip and s_ip.value and s_ip.value.strip():
                server_ip = s_ip.value.strip()
            
        # 2. If no setting or passed arg, use detected IP
        if not server_ip:
            server_ip = self.server_ip

        # Logic for Final Variables
        final_protocol = protocol if protocol else settings_map["protocol"]
        if final_protocol == "both": final_protocol = "udp"
        
        final_port = settings_map["port"] 

        # Build Config
        config = f"""client
dev tun
proto {final_protocol}
remote {server_ip} {final_port}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server

# Topology & routing
topology {settings_map['topology']}
"""
        if settings_map['redirect_gateway'] == '1':
            config += "redirect-gateway def1 bypass-dhcp\n"
            
        if settings_map['float'] == '1':
            config += "float\n"

        config += f"keepalive {settings_map['keepalive_interval']} {settings_map['keepalive_timeout']}\n"
        config += f"verb {settings_map['verb']}\n"

        config += f"""
# Security
auth {settings_map["auth_digest"]}
data-ciphers {settings_map["data_ciphers"]}
data-ciphers-fallback {settings_map.get('data_ciphers_fallback', 'AES-256-GCM')}
tls-version-min {settings_map["tls_version_min"]}
tls-client
"""
        if settings_map["compression"] != "none":
             config += f"compress {settings_map['compression']}\n"

        # DNS Settings (Flexible parsing)
        if settings_map.get("dns"):
             # Replace commas with spaces, then split
             dns_entries = settings_map["dns"].replace(',', ' ').split()
             for dns in dns_entries:
                 if dns.strip():
                     config += f"dhcp-option DNS {dns.strip()}\n"
        
        config += f"""
# Optimization
ignore-unknown-option block-outside-dns
block-outside-dns
key-direction 1
tun-mtu {settings_map['mtu']}
mssfix {int(settings_map['mtu']) - 40}

# Custom Configuration (from Admin Panel)
{settings_map['custom_config']}
"""

        # Scramble
        if settings_map["scramble"] == "1":
            config += 'scramble obfuscate "vpnmaster"\n'

        # Credentials & Certs
        config += """
# User Credentials
auth-user-pass

<ca>
"""
        config += f"{ca_cert}\n</ca>\n"

        if "BEGIN OpenVPN Static key" in tls_auth:
            config += f"<tls-auth>\n{tls_auth}\n</tls-auth>\n"
        
        return config

    def _write_static_key(self, path: str):
        """Generate OpenVPN Static Key (2048 bit) using Python"""
        import secrets
        
        # OpenVPN static key format
        # -----BEGIN OpenVPN Static key V1-----
        # hex strings ...
        # -----END OpenVPN Static key V1-----
        
        # Generate 256 bytes (2048 bits) of random data
        key_data = secrets.token_bytes(256)
        hex_data = key_data.hex()
        
        content = "-----BEGIN OpenVPN Static key V1-----\n"
        # Split into lines of 32 chars (16 bytes)
        for i in range(0, len(hex_data), 32):
            content += hex_data[i:i+32] + "\n"
        content += "-----END OpenVPN Static key V1-----\n"
        
        with open(path, "w") as f:
            f.write(content)

    def regenerate_pki(self):
        """Regenerate CA and Server Certificates"""
        logger.info("Regenerating OpenVPN PKI...")
        try:
            import subprocess
            import shutil
            
            # Ensure parent data directory exists
            os.makedirs(self.DATA_DIR, exist_ok=True)
            
            # FORCE REMOVE existing files to ensure no pollution
            for f in [self.CA_PATH, self.CA_KEY_PATH, self.TA_PATH]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception as rm_err:
                        logger.warning(f"Could not remove old file {f}: {rm_err}")

            # 1. Generate CA and Key
            # We use openssl req ... -keyout ... -out ...
            # -nodes ensures the key is not encrypted with a password
            subprocess.run(
                f"openssl req -new -x509 -days 3650 -nodes -text -out {self.CA_PATH} -keyout {self.CA_KEY_PATH} -subj '/CN=VPN-Master-Root-CA'",
                shell=True, check=True
            )
            
            # 2. Generate TLS Auth Key (ta.key) using Python
            self._write_static_key(self.TA_PATH)
            
            return True
        except Exception as e:
            logger.error(f"Failed to regenerate PKI: {e}")
            raise e

# Singleton instance
openvpn_service = OpenVPNService()
