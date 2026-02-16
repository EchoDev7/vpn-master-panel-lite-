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
        
        # Fetch settings from DB
        from ..database import get_db_context
        from ..models.setting import Setting
        
        protocol_setting = "udp"
        scramble = "0"
        mtu = "1500"
        
        with get_db_context() as db:
            s_proto = db.query(Setting).filter(Setting.key == "ovpn_protocol").first()
            if s_proto: protocol_setting = s_proto.value
            
            s_scramble = db.query(Setting).filter(Setting.key == "ovpn_scramble").first()
            if s_scramble: scramble = s_scramble.value
            
            s_mtu = db.query(Setting).filter(Setting.key == "ovpn_mtu").first()
            if s_mtu: mtu = s_mtu.value

            # Override server_ip if set in settings
            s_ip = db.query(Setting).filter(Setting.key == "wg_endpoint_ip").first() # Reuse endpoint ip setting
            if s_ip and s_ip.value: server_ip = s_ip.value

        # Determine protocol
        # If 'both' is selected, we default to the requested one, or UDP if not specified
        final_protocol = protocol if protocol else ("udp" if protocol_setting == "both" else protocol_setting)
        
        # Adjust port based on protocol (standard logic: 1194 UDP, 443 TCP commonly used)
        final_port = port
        if final_protocol == "tcp" and port == 1194:
            # If default UDP port was passed but we want TCP, maybe use 443 or user setting?
            # For now keep 1194 or let settings dictate. ideally we need ovpn_tcp_port and ovpn_udp_port
            pass 

        # Base Configuration Template with Best Practices
        config = f"""client
dev tun
proto {final_protocol}
remote {server_ip} {final_port}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
auth SHA256
cipher AES-256-GCM
ignore-unknown-option block-outside-dns
block-outside-dns
verb 3
key-direction 1
tun-mtu {mtu}
mssfix {int(mtu) - 40}
"""

        # Add Scramble/Obfuscation
        if scramble == "1":
            config += """
scramble obfuscate "vpnmaster"
"""

        # User Credentials
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

# Singleton instance
openvpn_service = OpenVPNService()
