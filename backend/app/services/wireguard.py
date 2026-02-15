"""
WireGuard VPN Service Implementation
"""
import subprocess
import os
import ipaddress
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class WireGuardService:
    """WireGuard VPN service manager"""
    
    CONFIG_DIR = "/etc/wireguard"
    INTERFACE = "wg0"
    
    def __init__(self):
        self.config_path = f"{self.CONFIG_DIR}/{self.INTERFACE}.conf"
        self.base_ip = ipaddress.IPv4Network("10.8.0.0/24")
        self.used_ips = set()
        
        # Ensure config directory exists
        Path(self.CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    
    def generate_keys(self) -> Dict[str, str]:
        """Generate WireGuard private and public keys"""
        try:
            # Generate private key
            private_key = subprocess.check_output(
                ["wg", "genkey"],
                text=True
            ).strip()
            
            # Generate public key from private
            public_key = subprocess.check_output(
                ["wg", "pubkey"],
                input=private_key,
                text=True
            ).strip()
            
            return {
                "private_key": private_key,
                "public_key": public_key
            }
            
        except Exception as e:
            logger.error(f"Failed to generate WireGuard keys: {e}")
            raise
    
    def allocate_ip(self) -> str:
        """Allocate next available IP address"""
        for ip in self.base_ip.hosts():
            if str(ip) not in self.used_ips:
                self.used_ips.add(str(ip))
                return str(ip)
        
        raise Exception("No available IP addresses")
    
    def add_peer(self, public_key: str, allowed_ip: str) -> bool:
        """Add peer to WireGuard interface"""
        try:
            subprocess.run([
                "wg", "set", self.INTERFACE,
                "peer", public_key,
                "allowed-ips", f"{allowed_ip}/32"
            ], check=True)
            
            # Save config
            subprocess.run([
                "wg-quick", "save", self.INTERFACE
            ], check=True)
            
            logger.info(f"Added WireGuard peer: {public_key[:16]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add WireGuard peer: {e}")
            return False
    
    def remove_peer(self, public_key: str) -> bool:
        """Remove peer from WireGuard interface"""
        try:
            subprocess.run([
                "wg", "set", self.INTERFACE,
                "peer", public_key,
                "remove"
            ], check=True)
            
            subprocess.run([
                "wg-quick", "save", self.INTERFACE
            ], check=True)
            
            logger.info(f"Removed WireGuard peer: {public_key[:16]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove WireGuard peer: {e}")
            return False
    
    def get_peer_stats(self, public_key: str) -> Optional[Dict[str, Any]]:
        """Get peer statistics"""
        try:
            output = subprocess.check_output(
                ["wg", "show", self.INTERFACE, "dump"],
                text=True
            )
            
            for line in output.splitlines()[1:]:  # Skip header
                parts = line.split('\t')
                if parts[0] == public_key:
                    return {
                        "public_key": parts[0],
                        "endpoint": parts[2] if len(parts) > 2 else None,
                        "allowed_ips": parts[3] if len(parts) > 3 else None,
                        "latest_handshake": int(parts[4]) if len(parts) > 4 else 0,
                        "transfer_rx": int(parts[5]) if len(parts) > 5 else 0,
                        "transfer_tx": int(parts[6]) if len(parts) > 6 else 0,
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get peer stats: {e}")
            return None
    
    def generate_client_config(
        self,
        client_private_key: str,
        client_ip: str,
        server_public_key: str,
        server_endpoint: str,
        server_port: int = 51820
    ) -> str:
        """Generate client configuration file"""
        config = f"""[Interface]
PrivateKey = {client_private_key}
Address = {client_ip}/24
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_endpoint}:{server_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
        return config


def generate_wireguard_keys() -> Dict[str, str]:
    """Helper function to generate WireGuard keys for a user"""
    service = WireGuardService()
    keys = service.generate_keys()
    keys['ip'] = service.allocate_ip()
    return keys
