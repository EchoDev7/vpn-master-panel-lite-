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

    def generate_client_config(
        self, 
        username: str, 
        password: str = None, # Not used in cert-auth (or used for inline logic if implemented)
        server_ip: str = None, 
        port: int = 1194, 
        protocol: str = "udp"
    ) -> str:
        """
        Generate .ovpn content
        """
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
        
        # Base Configuration Template
        config = f"""client
dev tun
proto {protocol}
remote {server_ip} {port}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
auth SHA256
cipher AES-256-GCM
verb 3

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
key-direction 1
"""
        
        return config

# Singleton instance
openvpn_service = OpenVPNService()
