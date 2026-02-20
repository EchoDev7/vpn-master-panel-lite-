"""
WireGuard VPN Service — Complete Implementation
Supports all WireGuard directives, Iran anti-censorship (wstunnel/udp2raw),
PresharedKey, QR code generation, server config, and live status.
"""
import subprocess
import os
import ipaddress
import base64
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# =============================================
# Default Settings (Iran-optimized)
# =============================================
WIREGUARD_DEFAULTS = {
    # Network
    "wg_port": "51820",
    "wg_mtu": "1380",
    "wg_interface": "wg0",
    "wg_subnet": "10.66.66.0",
    "wg_subnet_mask": "24",

    # DNS
    "wg_dns": "1.1.1.1,8.8.8.8",

    # Security
    "wg_preshared_key_enabled": "1",
    "wg_fwmark": "",

    # Connection
    "wg_persistent_keepalive": "25",
    "wg_save_config": "1",

    # Routing
    "wg_allowed_ips": "0.0.0.0/0,::/0",
    "wg_table": "auto",
    "wg_post_up": "",
    "wg_post_down": "",

    # Anti-Censorship / Obfuscation
    "wg_obfuscation_type": "none",
    "wg_obfuscation_port": "443",
    "wg_obfuscation_domain": "",

    # Server
    "wg_endpoint_ip": "",

    # Advanced
    "wg_custom_client_config": "",
    "wg_custom_server_config": "",
}


class WireGuardService:
    """Full-featured WireGuard VPN service manager"""

    CONFIG_DIR = "/etc/wireguard"
    DATA_DIR = "/opt/vpn-panel/data/wireguard"

    def __init__(self):
        # Defer the blocking network call — only resolve IP on first access
        self._server_ip: Optional[str] = None
        Path(self.CONFIG_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.DATA_DIR).mkdir(parents=True, exist_ok=True)

    @property
    def server_ip(self) -> str:
        """Lazily resolve the public IP (cached after first call)."""
        if self._server_ip is None:
            self._server_ip = self._get_public_ip()
        return self._server_ip

    # =============================================
    # Utilities
    # =============================================

    @staticmethod
    def _get_public_ip() -> str:
        """Detect server public IP"""
        for url in [
            "https://api.ipify.org",
            "https://ifconfig.me/ip",
            "https://icanhazip.com",
        ]:
            try:
                import requests
                return requests.get(url, timeout=3).text.strip()
            except Exception:
                continue
        return "YOUR_SERVER_IP"

    def _load_settings(self) -> Dict[str, str]:
        """Load WireGuard settings from database, merged with defaults"""
        settings = dict(WIREGUARD_DEFAULTS)
        try:
            from ..database import get_db_context
            from ..models.setting import Setting
            with get_db_context() as db:
                rows = db.query(Setting).filter(
                    Setting.key.startswith("wg_")
                ).all()
                for row in rows:
                    settings[row.key] = row.value
        except Exception as e:
            logger.warning(f"Could not load WG settings from DB: {e}")
        return settings

    def _get_interface(self, settings: Dict[str, str] = None) -> str:
        """Get WireGuard interface name"""
        if settings:
            return settings.get("wg_interface", "wg0")
        return "wg0"

    # =============================================
    # Key Management
    # =============================================

    def generate_keypair(self) -> Dict[str, str]:
        """Generate WireGuard private + public key pair"""
        try:
            private_key = subprocess.check_output(
                ["wg", "genkey"], text=True
            ).strip()
            public_key = subprocess.check_output(
                ["wg", "pubkey"], input=private_key, text=True
            ).strip()
            return {"private_key": private_key, "public_key": public_key}
        except FileNotFoundError:
            logger.warning("wg command not found, generating keys with Python")
            return self._generate_keys_python()
        except Exception as e:
            logger.error(f"Failed to generate WireGuard keys: {e}")
            raise

    def generate_preshared_key(self) -> str:
        """Generate a WireGuard preshared key for post-quantum resistance"""
        try:
            return subprocess.check_output(
                ["wg", "genpsk"], text=True
            ).strip()
        except FileNotFoundError:
            return self._generate_psk_python()
        except Exception as e:
            logger.error(f"Failed to generate preshared key: {e}")
            raise

    @staticmethod
    def _generate_keys_python() -> Dict[str, str]:
        """Fallback: generate Curve25519 keys using Python"""
        try:
            from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
            from cryptography.hazmat.primitives import serialization
            private = X25519PrivateKey.generate()
            private_bytes = private.private_bytes(
                serialization.Encoding.Raw,
                serialization.PrivateFormat.Raw,
                serialization.NoEncryption()
            )
            public_bytes = private.public_key().public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw
            )
            return {
                "private_key": base64.b64encode(private_bytes).decode(),
                "public_key": base64.b64encode(public_bytes).decode(),
            }
        except ImportError:
            private_key = base64.b64encode(os.urandom(32)).decode()
            return {"private_key": private_key, "public_key": "NEEDS_WG_TOOLS"}

    @staticmethod
    def _generate_psk_python() -> str:
        """Fallback: generate PSK using Python"""
        return base64.b64encode(os.urandom(32)).decode()

    def get_server_keys(self) -> Dict[str, str]:
        """Get or generate server keypair"""
        priv_path = os.path.join(self.CONFIG_DIR, "server_private.key")
        pub_path = os.path.join(self.CONFIG_DIR, "server_public.key")

        if os.path.exists(priv_path) and os.path.exists(pub_path):
            with open(priv_path, "r") as f:
                private_key = f.read().strip()
            with open(pub_path, "r") as f:
                public_key = f.read().strip()
            return {"private_key": private_key, "public_key": public_key}

        # Generate new keys
        keys = self.generate_keypair()
        try:
            os.makedirs(self.CONFIG_DIR, exist_ok=True)
            with open(priv_path, "w") as f:
                f.write(keys["private_key"])
            os.chmod(priv_path, 0o600)
            with open(pub_path, "w") as f:
                f.write(keys["public_key"])
            logger.info("✅ WireGuard server keys generated")
        except PermissionError:
            logger.warning("Cannot write server keys to /etc/wireguard (no root)")
        return keys

    def regenerate_server_keys(self) -> Dict[str, str]:
        """Force regenerate server keypair"""
        for f in ["server_private.key", "server_public.key"]:
            path = os.path.join(self.CONFIG_DIR, f)
            if os.path.exists(path):
                os.remove(path)
        return self.get_server_keys()

    # =============================================
    # IP Allocation
    # =============================================

    def allocate_ip(self, settings: Dict[str, str] = None) -> str:
        """Allocate next available IP from WireGuard subnet"""
        if not settings:
            settings = self._load_settings()

        subnet = settings.get("wg_subnet", "10.66.66.0")
        mask = settings.get("wg_subnet_mask", "24")
        network = ipaddress.IPv4Network(f"{subnet}/{mask}", strict=False)

        # Collect used IPs
        used_ips = {str(network.network_address), str(network.broadcast_address)}
        # Server always gets .1
        server_ip = str(list(network.hosts())[0])
        used_ips.add(server_ip)

        # Check DB for allocated IPs
        try:
            from ..database import get_db_context
            from ..models.user import User
            with get_db_context() as db:
                users = db.query(User.wireguard_ip).filter(
                    User.wireguard_ip.isnot(None)
                ).all()
                for (ip,) in users:
                    if ip:
                        used_ips.add(ip.split("/")[0])
        except Exception as e:
            logger.warning(f"Could not check DB for used IPs: {e}")

        # Find next available
        for host in network.hosts():
            ip_str = str(host)
            if ip_str not in used_ips:
                return ip_str

        raise Exception("No available IP addresses in WireGuard subnet")

    # =============================================
    # Server Configuration Generation
    # =============================================

    def generate_server_config(self) -> str:
        """Generate wg0.conf server configuration"""
        settings = self._load_settings()
        server_keys = self.get_server_keys()
        interface = self._get_interface(settings)

        subnet = settings.get("wg_subnet", "10.66.66.0")
        mask = settings.get("wg_subnet_mask", "24")
        port = settings.get("wg_port", "51820")
        mtu = settings.get("wg_mtu", "1380")
        fwmark = settings.get("wg_fwmark", "")
        table = settings.get("wg_table", "auto")
        save_config = settings.get("wg_save_config", "1")

        # Server IP is first host in subnet
        network = ipaddress.IPv4Network(f"{subnet}/{mask}", strict=False)
        server_ip = str(list(network.hosts())[0])

        lines = [
            "# =============================================",
            f"# WireGuard Server Config — {interface}",
            "# Generated by VPN Master Panel",
            "# =============================================",
            "",
            "[Interface]",
            f"PrivateKey = {server_keys['private_key']}",
            f"Address = {server_ip}/{mask}",
            f"ListenPort = {port}",
            f"MTU = {mtu}",
        ]

        if save_config == "1":
            lines.append("SaveConfig = true")

        if fwmark:
            lines.append(f"FwMark = {fwmark}")

        if table and table != "auto":
            lines.append(f"Table = {table}")

        # PostUp / PostDown (NAT + Firewall)
        post_up = settings.get("wg_post_up", "").strip()
        post_down = settings.get("wg_post_down", "").strip()

        if post_up:
            lines.append(f"PostUp = {post_up}")
        else:
            # Default: enable NAT masquerade
            lines.append(
                f"PostUp = iptables -t nat -A POSTROUTING -s {subnet}/{mask} "
                f"-o $(ip -4 route ls | grep default | grep -Po '(?<=dev )\\S+' | head -1) -j MASQUERADE; "
                f"iptables -A INPUT -p udp --dport {port} -j ACCEPT; "
                f"iptables -A FORWARD -i {interface} -j ACCEPT; "
                f"iptables -A FORWARD -o {interface} -j ACCEPT"
            )

        if post_down:
            lines.append(f"PostDown = {post_down}")
        else:
            lines.append(
                f"PostDown = iptables -t nat -D POSTROUTING -s {subnet}/{mask} "
                f"-o $(ip -4 route ls | grep default | grep -Po '(?<=dev )\\S+' | head -1) -j MASQUERADE; "
                f"iptables -D INPUT -p udp --dport {port} -j ACCEPT; "
                f"iptables -D FORWARD -i {interface} -j ACCEPT; "
                f"iptables -D FORWARD -o {interface} -j ACCEPT"
            )

        # Custom server directives
        custom = settings.get("wg_custom_server_config", "").strip()
        if custom:
            lines.append("")
            lines.append("# Custom directives")
            lines.extend(custom.split("\n"))

        # Add existing peers from DB
        lines.extend(self._get_peer_sections(settings))

        return "\n".join(lines)

    def _get_peer_sections(self, settings: Dict[str, str]) -> List[str]:
        """Generate [Peer] sections for all active WireGuard users"""
        lines = []
        try:
            from ..database import get_db_context
            from ..models.user import User
            with get_db_context() as db:
                users = db.query(User).filter(
                    User.wireguard_enabled == True,
                    User.wireguard_public_key.isnot(None),
                    User.wireguard_ip.isnot(None),
                ).all()

                for user in users:
                    lines.append("")
                    lines.append(f"# Peer: {user.username}")
                    lines.append("[Peer]")
                    lines.append(f"PublicKey = {user.wireguard_public_key}")

                    # PresharedKey
                    if (settings.get("wg_preshared_key_enabled", "1") == "1"
                            and hasattr(user, 'wireguard_preshared_key')
                            and user.wireguard_preshared_key):
                        lines.append(f"PresharedKey = {user.wireguard_preshared_key}")

                    ip = user.wireguard_ip.split("/")[0]
                    lines.append(f"AllowedIPs = {ip}/32")

                    keepalive = settings.get("wg_persistent_keepalive", "25")
                    if keepalive and keepalive != "0":
                        lines.append(f"PersistentKeepalive = {keepalive}")

        except Exception as e:
            logger.warning(f"Could not load peers from DB: {e}")
        return lines

    # =============================================
    # Client Configuration Generation
    # =============================================

    def generate_client_config(
        self,
        client_private_key: str,
        client_ip: str,
        server_public_key: str = None,
        preshared_key: str = None,
        server_endpoint: str = None,
    ) -> str:
        """Generate complete client .conf with all settings from DB"""
        settings = self._load_settings()

        # Resolve server keys and IP
        if not server_public_key:
            server_keys = self.get_server_keys()
            server_public_key = server_keys["public_key"]

        endpoint_ip = settings.get("wg_endpoint_ip", "").strip()
        if not endpoint_ip:
            endpoint_ip = server_endpoint or self.server_ip

        port = settings.get("wg_port", "51820")
        mtu = settings.get("wg_mtu", "1380")
        dns = settings.get("wg_dns", "1.1.1.1,8.8.8.8")
        mask = settings.get("wg_subnet_mask", "24")
        allowed_ips = settings.get("wg_allowed_ips", "0.0.0.0/0,::/0")
        keepalive = settings.get("wg_persistent_keepalive", "25")
        obfuscation = settings.get("wg_obfuscation_type", "none")

        # Clean client IP
        client_ip_clean = client_ip.split("/")[0]

        lines = [
            "# =============================================",
            "# WireGuard Client Config",
            "# Generated by VPN Master Panel",
            "# =============================================",
            "",
            "[Interface]",
            f"PrivateKey = {client_private_key}",
            f"Address = {client_ip_clean}/{mask}",
            f"DNS = {dns.replace(',', ', ')}",
            f"MTU = {mtu}",
        ]

        # Obfuscation: client-side scripts
        if obfuscation == "wstunnel":
            obfs_port = settings.get("wg_obfuscation_port", "443")
            obfs_domain = settings.get("wg_obfuscation_domain", endpoint_ip)
            lines.append("")
            lines.append("# Anti-Censorship: wstunnel (WebSocket over HTTPS)")
            lines.append(f"# Connect wstunnel first: wstunnel client -L udp://127.0.0.1:51820:127.0.0.1:{port} wss://{obfs_domain}:{obfs_port}")
            lines.append("# Then use this config with Endpoint = 127.0.0.1:51820")

        elif obfuscation == "udp2raw":
            obfs_port = settings.get("wg_obfuscation_port", "443")
            lines.append("")
            lines.append("# Anti-Censorship: udp2raw (FakeTCP)")
            lines.append(f"# Connect udp2raw first: udp2raw -c -l 127.0.0.1:51820 -r {endpoint_ip}:{obfs_port} --raw-mode faketcp -a -k vpnmaster")
            lines.append("# Then use this config with Endpoint = 127.0.0.1:51820")

        lines.append("")
        lines.append("[Peer]")
        lines.append(f"PublicKey = {server_public_key}")

        # PresharedKey
        psk_enabled = settings.get("wg_preshared_key_enabled", "1")
        if psk_enabled == "1" and preshared_key:
            lines.append(f"PresharedKey = {preshared_key}")

        # Endpoint — adjusted for obfuscation
        if obfuscation in ("wstunnel", "udp2raw"):
            lines.append(f"Endpoint = 127.0.0.1:{port}")
        else:
            lines.append(f"Endpoint = {endpoint_ip}:{port}")

        # AllowedIPs
        lines.append(f"AllowedIPs = {allowed_ips.replace(',', ', ')}")

        # PersistentKeepalive
        if keepalive and keepalive != "0":
            lines.append(f"PersistentKeepalive = {keepalive}")

        # Custom client directives
        custom = settings.get("wg_custom_client_config", "").strip()
        if custom:
            lines.append("")
            lines.append("# Custom directives")
            lines.extend(custom.split("\n"))

        return "\n".join(lines)

    # =============================================
    # QR Code Generation
    # =============================================

    def generate_qr_code(self, config_text: str) -> Optional[str]:
        """Generate QR code as base64 PNG for mobile import"""
        try:
            import qrcode
            from io import BytesIO

            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(config_text)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            return base64.b64encode(buffer.getvalue()).decode()
        except ImportError:
            logger.warning("qrcode library not installed. Install: pip install qrcode[pil]")
            # Fallback: use qrencode CLI
            try:
                result = subprocess.run(
                    ["qrencode", "-t", "PNG", "-o", "-"],
                    input=config_text.encode(),
                    capture_output=True,
                )
                if result.returncode == 0:
                    return base64.b64encode(result.stdout).decode()
            except FileNotFoundError:
                pass
            return None

    # =============================================
    # Peer Management
    # =============================================

    def add_peer(
        self, public_key: str, allowed_ip: str,
        preshared_key: str = None, settings: Dict[str, str] = None,
    ) -> bool:
        """Add peer to WireGuard interface at runtime"""
        if not settings:
            settings = self._load_settings()
        interface = self._get_interface(settings)

        try:
            cmd = [
                "wg", "set", interface,
                "peer", public_key,
                "allowed-ips", f"{allowed_ip}/32",
            ]

            if preshared_key:
                # wg set requires preshared-key from a file
                psk_file = os.path.join(self.DATA_DIR, f"psk_{public_key[:8]}.key")
                with open(psk_file, "w") as f:
                    f.write(preshared_key)
                os.chmod(psk_file, 0o600)
                cmd.extend(["preshared-key", psk_file])

            keepalive = settings.get("wg_persistent_keepalive", "25")
            if keepalive and keepalive != "0":
                cmd.extend(["persistent-keepalive", keepalive])

            subprocess.run(cmd, check=True)

            # Save config
            if settings.get("wg_save_config", "1") == "1":
                subprocess.run(["wg-quick", "save", interface], check=True)

            logger.info(f"✅ Added WireGuard peer: {public_key[:16]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to add WireGuard peer: {e}")
            return False

    def remove_peer(self, public_key: str) -> bool:
        """Remove peer from WireGuard interface"""
        settings = self._load_settings()
        interface = self._get_interface(settings)

        try:
            subprocess.run([
                "wg", "set", interface,
                "peer", public_key, "remove"
            ], check=True)

            if settings.get("wg_save_config", "1") == "1":
                subprocess.run(["wg-quick", "save", interface], check=True)

            # Remove PSK file if exists
            psk_file = os.path.join(self.DATA_DIR, f"psk_{public_key[:8]}.key")
            if os.path.exists(psk_file):
                os.remove(psk_file)

            logger.info(f"✅ Removed WireGuard peer: {public_key[:16]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to remove WireGuard peer: {e}")
            return False

    # =============================================
    # Interface Management
    # =============================================

    def start_interface(self) -> bool:
        """Start WireGuard interface via wg-quick"""
        settings = self._load_settings()
        interface = self._get_interface(settings)
        try:
            subprocess.run(["wg-quick", "up", interface], check=True)
            logger.info(f"✅ WireGuard {interface} started")
            return True
        except Exception as e:
            logger.error(f"Failed to start WireGuard: {e}")
            return False

    def stop_interface(self) -> bool:
        """Stop WireGuard interface"""
        settings = self._load_settings()
        interface = self._get_interface(settings)
        try:
            subprocess.run(["wg-quick", "down", interface], check=True)
            logger.info(f"✅ WireGuard {interface} stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop WireGuard: {e}")
            return False

    def restart_interface(self) -> bool:
        """Restart WireGuard interface"""
        self.stop_interface()
        time.sleep(1)
        return self.start_interface()

    # =============================================
    # Status & Monitoring
    # =============================================

    def get_interface_status(self) -> Dict[str, Any]:
        """Get WireGuard interface status and all peer stats"""
        settings = self._load_settings()
        interface = self._get_interface(settings)

        result = {
            "interface": interface,
            "running": False,
            "public_key": "",
            "listen_port": 0,
            "peers": [],
            "total_transfer_rx": 0,
            "total_transfer_tx": 0,
        }

        try:
            output = subprocess.check_output(
                ["wg", "show", interface, "dump"], text=True
            )
            lines = output.strip().split("\n")
            if not lines:
                return result

            result["running"] = True

            # First line: interface info
            # private-key  public-key  listen-port  fwmark
            parts = lines[0].split("\t")
            if len(parts) >= 3:
                result["public_key"] = parts[1]
                result["listen_port"] = int(parts[2])

            # Remaining lines: peer info
            # public-key  preshared-key  endpoint  allowed-ips  latest-handshake  transfer-rx  transfer-tx  persistent-keepalive
            for line in lines[1:]:
                parts = line.split("\t")
                if len(parts) < 7:
                    continue

                peer = {
                    "public_key": parts[0],
                    "preshared_key": parts[1] != "(none)",
                    "endpoint": parts[2] if parts[2] != "(none)" else None,
                    "allowed_ips": parts[3],
                    "latest_handshake": int(parts[4]) if parts[4] != "0" else 0,
                    "transfer_rx": int(parts[5]),
                    "transfer_tx": int(parts[6]),
                    "persistent_keepalive": parts[7] if len(parts) > 7 and parts[7] != "off" else None,
                }

                # Human-readable handshake time
                if peer["latest_handshake"] > 0:
                    ago = int(time.time()) - peer["latest_handshake"]
                    if ago < 60:
                        peer["handshake_ago"] = f"{ago}s ago"
                    elif ago < 3600:
                        peer["handshake_ago"] = f"{ago // 60}m ago"
                    else:
                        peer["handshake_ago"] = f"{ago // 3600}h ago"
                    peer["is_online"] = ago < 180  # 3 minute threshold
                else:
                    peer["handshake_ago"] = "never"
                    peer["is_online"] = False

                # Human-readable transfer
                peer["transfer_rx_human"] = self._human_bytes(peer["transfer_rx"])
                peer["transfer_tx_human"] = self._human_bytes(peer["transfer_tx"])

                result["total_transfer_rx"] += peer["transfer_rx"]
                result["total_transfer_tx"] += peer["transfer_tx"]
                result["peers"].append(peer)

            result["total_transfer_rx_human"] = self._human_bytes(result["total_transfer_rx"])
            result["total_transfer_tx_human"] = self._human_bytes(result["total_transfer_tx"])

        except subprocess.CalledProcessError:
            result["running"] = False
        except FileNotFoundError:
            result["running"] = False
            result["error"] = "wg command not found"
        except Exception as e:
            result["error"] = str(e)

        return result

    def get_peer_stats(self, public_key: str) -> Optional[Dict[str, Any]]:
        """Get stats for a specific peer"""
        status = self.get_interface_status()
        for peer in status.get("peers", []):
            if peer["public_key"] == public_key:
                return peer
        return None

    @staticmethod
    def _human_bytes(n: int) -> str:
        """Convert bytes to human-readable format"""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024:
                return f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} PB"

    # =============================================
    # Obfuscation Helpers
    # =============================================

    def generate_obfuscation_setup_script(self) -> str:
        """Generate bash script to set up obfuscation on the server"""
        settings = self._load_settings()
        obfs_type = settings.get("wg_obfuscation_type", "none")
        port = settings.get("wg_port", "51820")
        obfs_obfuscation_port = settings.get("wg_obfuscation_port", "443")
        domain = settings.get("wg_obfuscation_domain", "")

        # SHA256 Checksums (Update these when bumping versions)
        WSTUNNEL_VERSION = "v5.0" # Example version, adjust as needed
        # WSTUNNEL_SHA256 = "..." 
        
        # UDP2RAW_VERSION = "20230206.0"
        # UDP2RAW_SHA256 = "..."

        if obfs_type == "wstunnel":
            return f"""#!/bin/bash
# WireGuard + wstunnel (WebSocket over HTTPS) Setup
# This tunnels WG UDP traffic through WebSocket/TLS

# Install wstunnel (Pinned Version)
WSTUNNEL_URL="https://github.com/erebe/wstunnel/releases/download/v9.0.0/wstunnel-linux-x64"
wget -q $WSTUNNEL_URL -O /usr/local/bin/wstunnel
chmod +x /usr/local/bin/wstunnel

# Run wstunnel server (forward WebSocket → WG UDP)
# wstunnel server --restrict-to 127.0.0.1:{port} wss://0.0.0.0:{obfs_obfuscation_port}

# Create systemd service
cat > /etc/systemd/system/wstunnel.service << 'EOF'
[Unit]
Description=WStunnel WebSocket Tunnel for WireGuard
After=network.target

[Service]
ExecStart=/usr/local/bin/wstunnel server --restrict-to 127.0.0.1:{port} wss://0.0.0.0:{obfs_obfuscation_port}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now wstunnel

echo "✅ wstunnel configured on port {obfs_obfuscation_port} → WireGuard port {port}"
"""
        elif obfs_type == "udp2raw":
            return f"""#!/bin/bash
# WireGuard + udp2raw (FakeTCP) Setup
# This encapsulates WG UDP in fake TCP packets

# Install udp2raw (Pinned Version)
UDP2RAW_URL="https://github.com/wangyu-/udp2raw/releases/download/20230206.0/udp2raw_binaries.tar.gz"
wget -q $UDP2RAW_URL -O /tmp/udp2raw.tar.gz
tar xzf /tmp/udp2raw.tar.gz -C /usr/local/bin/ udp2raw_amd64
mv /usr/local/bin/udp2raw_amd64 /usr/local/bin/udp2raw
chmod +x /usr/local/bin/udp2raw

# Create systemd service
cat > /etc/systemd/system/udp2raw.service << 'EOF'
[Unit]
Description=UDP2RAW FakeTCP Tunnel for WireGuard
After=network.target

[Service]
ExecStart=/usr/local/bin/udp2raw -s -l 0.0.0.0:{obfs_obfuscation_port} -r 127.0.0.1:{port} --raw-mode faketcp -a -k vpnmaster
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now udp2raw

echo "✅ udp2raw configured on port {obfs_obfuscation_port} (FakeTCP) → WireGuard port {port}"
"""
        else:
            return "# No obfuscation configured"


# =============================================
# Module-level singleton & helper
# =============================================

wireguard_service = WireGuardService()


def generate_wireguard_keys() -> Dict[str, str]:
    """Legacy helper: generate keys + allocate IP"""
    keys = wireguard_service.generate_keypair()
    keys["ip"] = wireguard_service.allocate_ip()
    # Generate PSK if enabled
    settings = wireguard_service._load_settings()
    if settings.get("wg_preshared_key_enabled", "1") == "1":
        keys["preshared_key"] = wireguard_service.generate_preshared_key()
    return keys
