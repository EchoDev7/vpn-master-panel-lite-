"""
OpenVPN Service - Complete Configuration Generator
Optimized for anti-censorship (Iran DPI bypass)

Supports:
- Client .ovpn generation with all admin-configurable settings
- Server server.conf generation
- TLS control channel security (tls-auth / tls-crypt / tls-crypt-v2)
- XOR Scramble with custom password
- Fragment/mssfix for DPI evasion
- Multi-remote failover
- Proxy chaining (SOCKS5 / HTTP)
- Full routing and DNS control
"""
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# ====================================================================
# All configurable OpenVPN settings with defaults (Iran-optimized)
# ====================================================================
OPENVPN_DEFAULTS: Dict[str, str] = {
    # --- Network ---
    "protocol": "tcp",              # tcp for port 443 stealth
    "port": "443",                  # HTTPS port to blend with normal traffic
    "mtu": "1400",                  # Lower MTU for Iran mobile/ISP networks
    "topology": "subnet",           # subnet (recommended) or net30
    "float": "1",                   # Allow client IP change (mobile networks)
    "server_subnet": "10.8.0.0",    # VPN subnet
    "server_netmask": "255.255.255.0",
    "max_clients": "100",           # Maximum concurrent connections
    "duplicate_cn": "1",            # Allow same user from multiple devices

    # --- Security & Encryption ---
    "data_ciphers": "AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305",
    "data_ciphers_fallback": "AES-256-GCM",
    "auth_digest": "SHA256",        # HMAC digest
    "tls_version_min": "1.2",
    "tls_ciphers": "TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384:TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384",
    "tls_cipher_suites": "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256",  # TLS 1.3
    "reneg_sec": "3600",            # Renegotiate TLS session every hour

    # --- TLS Control Channel (Critical for anti-censorship) ---
    "tls_control_channel": "tls-crypt",  # none / tls-auth / tls-crypt / tls-crypt-v2

    # --- Anti-Censorship (Iran-specific) ---
    "scramble": "1",                # Enable XOR scramble
    "scramble_password": "vpnmaster",  # XOR scramble password
    "fragment": "0",                # 0=disabled, or size (e.g. 1200) to fragment packets
    "port_share": "",               # e.g. "127.0.0.1 8443" to share port with HTTPS

    # --- Routing & DNS ---
    "redirect_gateway": "1",        # 1=route all traffic through VPN
    "dns": "1.1.1.1,8.8.8.8",      # DNS servers pushed to clients
    "block_outside_dns": "1",       # Prevent DNS leaks on Windows
    "inter_client": "0",            # Allow client-to-client communication

    # --- Connection & Keepalive ---
    "keepalive_interval": "10",
    "keepalive_timeout": "60",
    "connect_retry": "5",           # Retry connection every N seconds
    "connect_retry_max": "0",       # 0 = infinite retries
    "server_poll_timeout": "10",    # Timeout waiting for server response
    "verb": "3",                    # Log verbosity (1-6)
    "compression": "none",          # none / lz4-v2 / lzo

    # --- Proxy ---
    "proxy_type": "none",           # none / socks / http
    "proxy_address": "",            # Proxy address
    "proxy_port": "",               # Proxy port

    # --- Multi-Remote (failover servers) ---
    "remote_servers": "",           # Comma-separated: "ip1:port1:proto1,ip2:port2:proto2"

    # --- Advanced ---
    "custom_client_config": "",     # Raw directives injected into client config
    "custom_server_config": "",     # Raw directives injected into server config

    # --- Server IP ---
    "server_ip": "",                # Override server public IP (empty=auto-detect)
}


class OpenVPNService:
    """OpenVPN Configuration Generator — Anti-Censorship Edition"""

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, "data", "openvpn")
    CA_PATH = os.path.join(DATA_DIR, "ca.crt")
    CA_KEY_PATH = os.path.join(DATA_DIR, "ca.key")
    TA_PATH = os.path.join(DATA_DIR, "ta.key")

    def __init__(self):
        self.server_ip = self._get_public_ip()

    # ================================================================
    # Helpers
    # ================================================================

    def _get_public_ip(self) -> str:
        """Get server public IP with multiple fallbacks"""
        import socket
        try:
            import requests
            for url in ['https://api.ipify.org', 'https://checkip.amazonaws.com']:
                try:
                    return requests.get(url, timeout=3).text.strip()
                except Exception:
                    continue
            # Fallback: local socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
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
        try:
            self.regenerate_pki()
        except Exception as e:
            logger.error(f"Auto-generation of PKI failed: {e}")

    def _load_settings(self) -> Dict[str, str]:
        """Load all OpenVPN settings from DB, merged with defaults"""
        settings = dict(OPENVPN_DEFAULTS)

        from ..database import get_db_context
        from ..models.setting import Setting

        with get_db_context() as db:
            all_settings = db.query(Setting).all()
            for s in all_settings:
                if s.key.startswith("ovpn_"):
                    key = s.key[5:]  # Remove "ovpn_" prefix
                    if key in settings:
                        settings[key] = s.value

                # Also check for server IP override
                if s.key == "wg_endpoint_ip" and s.value and s.value.strip():
                    settings["server_ip"] = s.value.strip()

        return settings

    def _resolve_server_ip(self, settings: Dict[str, str], override: str = None) -> str:
        """Determine the server IP to use"""
        if override:
            return override
        if settings.get("server_ip"):
            return settings["server_ip"]
        return self.server_ip

    # ================================================================
    # Client Config Generation
    # ================================================================

    def generate_client_config(
        self,
        username: str,
        password: str = None,
        server_ip: str = None,
        port: int = None,
        protocol: str = None
    ) -> str:
        """
        Generate complete .ovpn client configuration.
        All settings come from admin panel (DB) with anti-censorship defaults.
        """
        self._ensure_pki()
        settings = self._load_settings()

        # Read certificates
        ca_cert = self._read_file(self.CA_PATH)
        tls_key = self._read_file(self.TA_PATH)

        # Resolve connection parameters
        final_ip = self._resolve_server_ip(settings, server_ip)
        final_port = str(port) if port else settings["port"]
        final_proto = protocol if protocol else settings["protocol"]
        if final_proto == "both":
            final_proto = "tcp"

        # ---- Build Config ----
        lines = []
        lines.append("# ===================================================")
        lines.append(f"# OpenVPN Client Config — {username}")
        lines.append("# Generated by VPN Master Panel")
        lines.append("# Anti-Censorship Edition (Iran Optimized)")
        lines.append("# ===================================================")
        lines.append("")
        lines.append("client")
        lines.append("dev tun")
        lines.append(f"proto {final_proto}")

        # Multi-remote failover
        remote_servers = settings.get("remote_servers", "").strip()
        if remote_servers:
            for entry in remote_servers.split(","):
                entry = entry.strip()
                if entry:
                    parts = entry.split(":")
                    if len(parts) == 3:
                        lines.append(f"remote {parts[0]} {parts[1]} {parts[2]}")
                    elif len(parts) == 2:
                        lines.append(f"remote {parts[0]} {parts[1]}")
                    else:
                        lines.append(f"remote {entry} {final_port}")
            # Also add main server as fallback
            lines.append(f"remote {final_ip} {final_port}")
            lines.append("remote-random")
        else:
            lines.append(f"remote {final_ip} {final_port}")

        lines.append("resolv-retry infinite")
        lines.append("nobind")
        lines.append("persist-key")
        lines.append("persist-tun")
        lines.append("remote-cert-tls server")
        lines.append("")

        # --- Topology & Routing ---
        lines.append("# Topology & Routing")
        lines.append(f"topology {settings['topology']}")
        if settings["redirect_gateway"] == "1":
            lines.append("redirect-gateway def1 bypass-dhcp")
        if settings["float"] == "1":
            lines.append("float")

        lines.append("")

        # --- Connection ---
        lines.append("# Connection")
        lines.append(f"keepalive {settings['keepalive_interval']} {settings['keepalive_timeout']}")
        lines.append(f"verb {settings['verb']}")

        connect_retry = settings.get("connect_retry", "5")
        connect_retry_max = settings.get("connect_retry_max", "0")
        if connect_retry_max == "0":
            lines.append(f"connect-retry {connect_retry}")
        else:
            lines.append(f"connect-retry {connect_retry} {connect_retry_max}")

        server_poll = settings.get("server_poll_timeout", "10")
        lines.append(f"server-poll-timeout {server_poll}")

        # Reneg interval
        reneg = settings.get("reneg_sec", "3600")
        lines.append(f"reneg-sec {reneg}")

        lines.append("")

        # --- Security & Encryption ---
        lines.append("# Security & Encryption")
        lines.append(f"auth {settings['auth_digest']}")
        lines.append(f"data-ciphers {settings['data_ciphers']}")
        lines.append(f"data-ciphers-fallback {settings['data_ciphers_fallback']}")
        lines.append(f"tls-version-min {settings['tls_version_min']}")
        lines.append("tls-client")

        # TLS cipher suites (if TLS 1.3 is in play)
        if settings.get("tls_cipher_suites"):
            lines.append(f"tls-ciphersuites {settings['tls_cipher_suites']}")
        if settings.get("tls_ciphers"):
            lines.append(f"tls-cipher {settings['tls_ciphers']}")

        lines.append("")

        # --- Anti-Censorship ---
        lines.append("# Anti-Censorship")

        # Fragment (split packets to avoid DPI fingerprinting)
        frag = settings.get("fragment", "0")
        if frag and frag != "0":
            lines.append(f"fragment {frag}")
            lines.append(f"mssfix {frag}")
        else:
            # Default mssfix based on MTU
            mtu = int(settings.get("mtu", "1400"))
            lines.append(f"tun-mtu {mtu}")
            lines.append(f"mssfix {mtu - 40}")

        # XOR Scramble
        if settings["scramble"] == "1":
            scram_pwd = settings.get("scramble_password", "vpnmaster")
            lines.append(f'scramble obfuscate "{scram_pwd}"')

        lines.append("")

        # --- DNS ---
        dns_raw = settings.get("dns", "")
        if dns_raw:
            lines.append("# DNS")
            dns_entries = dns_raw.replace(",", " ").split()
            for dns in dns_entries:
                dns = dns.strip()
                if dns:
                    lines.append(f"dhcp-option DNS {dns}")

        # Block outside DNS (Windows DNS leak prevention)
        if settings.get("block_outside_dns", "1") == "1":
            lines.append("ignore-unknown-option block-outside-dns")
            lines.append("block-outside-dns")

        lines.append("")

        # --- Compression ---
        comp = settings.get("compression", "none")
        if comp and comp != "none":
            lines.append(f"compress {comp}")

        # --- Proxy ---
        proxy_type = settings.get("proxy_type", "none")
        proxy_addr = settings.get("proxy_address", "")
        proxy_port_str = settings.get("proxy_port", "")
        if proxy_type != "none" and proxy_addr and proxy_port_str:
            lines.append("")
            lines.append("# Proxy")
            if proxy_type == "socks":
                lines.append(f"socks-proxy {proxy_addr} {proxy_port_str}")
            elif proxy_type == "http":
                lines.append(f"http-proxy {proxy_addr} {proxy_port_str}")

        # --- Custom Client Config ---
        custom = settings.get("custom_client_config", "").strip()
        if custom:
            lines.append("")
            lines.append("# Custom Configuration (Admin Panel)")
            lines.append(custom)

        # --- Credentials ---
        lines.append("")
        lines.append("# Authentication")
        lines.append("auth-user-pass")
        lines.append("")

        # --- TLS Control Channel + Certificates ---
        tls_mode = settings.get("tls_control_channel", "tls-crypt")

        # CA Certificate
        lines.append("<ca>")
        lines.append(ca_cert)
        lines.append("</ca>")
        lines.append("")

        # TLS Key (based on mode)
        if tls_mode == "tls-crypt" and "BEGIN OpenVPN Static key" in tls_key:
            lines.append("<tls-crypt>")
            lines.append(tls_key)
            lines.append("</tls-crypt>")
        elif tls_mode == "tls-crypt-v2" and "BEGIN OpenVPN Static key" in tls_key:
            # tls-crypt-v2 uses per-client keys; for now fall back to tls-crypt format
            lines.append("<tls-crypt>")
            lines.append(tls_key)
            lines.append("</tls-crypt>")
        elif tls_mode == "tls-auth" and "BEGIN OpenVPN Static key" in tls_key:
            lines.append("key-direction 1")
            lines.append("<tls-auth>")
            lines.append(tls_key)
            lines.append("</tls-auth>")
        # else: tls_mode == "none" → no TLS key added

        lines.append("")
        return "\n".join(lines)

    # ================================================================
    # Server Config Generation
    # ================================================================

    def generate_server_config(self) -> str:
        """
        Generate complete server.conf for OpenVPN server.
        All settings come from admin panel (DB).
        """
        settings = self._load_settings()

        final_proto = settings["protocol"]
        if final_proto == "both":
            final_proto = "udp"  # Server default

        lines = []
        lines.append("# ===================================================")
        lines.append("# OpenVPN Server Config")
        lines.append("# Generated by VPN Master Panel")
        lines.append("# ===================================================")
        lines.append("")

        # --- Core ---
        lines.append(f"port {settings['port']}")
        lines.append(f"proto {final_proto}")
        lines.append("dev tun")
        lines.append("")

        # --- PKI ---
        lines.append("# Certificates")
        lines.append(f"ca {self.CA_PATH}")
        # Server cert/key paths (if separate from CA)
        server_cert = os.path.join(self.DATA_DIR, "server.crt")
        server_key = os.path.join(self.DATA_DIR, "server.key")
        dh_path = os.path.join(self.DATA_DIR, "dh.pem")
        lines.append(f"cert {server_cert}")
        lines.append(f"key {server_key}")
        lines.append(f"dh {dh_path}")
        lines.append("")

        # --- TLS Control Channel ---
        tls_mode = settings.get("tls_control_channel", "tls-crypt")
        if tls_mode == "tls-crypt":
            lines.append(f"tls-crypt {self.TA_PATH}")
        elif tls_mode == "tls-auth":
            lines.append(f"tls-auth {self.TA_PATH} 0")
        elif tls_mode == "tls-crypt-v2":
            lines.append(f"tls-crypt {self.TA_PATH}")  # Fallback
        lines.append("")

        # --- Network ---
        lines.append("# Network")
        lines.append(f"server {settings['server_subnet']} {settings['server_netmask']}")
        lines.append(f"topology {settings['topology']}")
        lines.append(f"max-clients {settings['max_clients']}")
        if settings.get("duplicate_cn", "0") == "1":
            lines.append("duplicate-cn")
        lines.append("ifconfig-pool-persist /var/log/openvpn/ipp.txt")
        lines.append("")

        # --- Port Sharing ---
        port_share = settings.get("port_share", "").strip()
        if port_share:
            lines.append(f"port-share {port_share}")
            lines.append("")

        # --- Security ---
        lines.append("# Security")
        lines.append(f"auth {settings['auth_digest']}")
        lines.append(f"data-ciphers {settings['data_ciphers']}")
        lines.append(f"data-ciphers-fallback {settings['data_ciphers_fallback']}")
        lines.append(f"tls-version-min {settings['tls_version_min']}")
        if settings.get("tls_ciphers"):
            lines.append(f"tls-cipher {settings['tls_ciphers']}")
        if settings.get("tls_cipher_suites"):
            lines.append(f"tls-ciphersuites {settings['tls_cipher_suites']}")
        lines.append(f"reneg-sec {settings.get('reneg_sec', '3600')}")
        lines.append("")

        # --- Routing ---
        lines.append("# Routing & DNS")
        if settings["redirect_gateway"] == "1":
            lines.append('push "redirect-gateway def1 bypass-dhcp"')
        dns_raw = settings.get("dns", "")
        if dns_raw:
            for dns in dns_raw.replace(",", " ").split():
                dns = dns.strip()
                if dns:
                    lines.append(f'push "dhcp-option DNS {dns}"')
        if settings.get("block_outside_dns", "1") == "1":
            lines.append('push "block-outside-dns"')
        if settings.get("inter_client", "0") == "1":
            lines.append("client-to-client")
        lines.append("")

        # --- Keepalive ---
        lines.append("# Connection")
        lines.append(f"keepalive {settings['keepalive_interval']} {settings['keepalive_timeout']}")
        lines.append(f"verb {settings['verb']}")
        lines.append("")

        # --- MTU / Fragment ---
        lines.append("# MTU & Fragment")
        frag = settings.get("fragment", "0")
        mtu = int(settings.get("mtu", "1400"))
        lines.append(f"tun-mtu {mtu}")
        if frag and frag != "0":
            lines.append(f"fragment {frag}")
            lines.append(f"mssfix {frag}")
        else:
            lines.append(f"mssfix {mtu - 40}")
        lines.append("")

        # --- Compression ---
        comp = settings.get("compression", "none")
        if comp and comp != "none":
            lines.append(f"compress {comp}")
            lines.append(f'push "compress {comp}"')
            lines.append("")

        # --- XOR Scramble ---
        if settings.get("scramble", "0") == "1":
            scram_pwd = settings.get("scramble_password", "vpnmaster")
            lines.append(f'scramble obfuscate "{scram_pwd}"')
            lines.append("")

        # --- Persistence & Logging ---
        lines.append("# Operations")
        lines.append("persist-key")
        lines.append("persist-tun")
        lines.append("status /var/log/openvpn/openvpn-status.log")
        lines.append("log-append /var/log/openvpn/openvpn.log")
        lines.append("user nobody")
        lines.append("group nogroup")
        lines.append("")

        # --- Auth via script (user/pass from panel DB) ---
        lines.append("# User authentication via script")
        lines.append("plugin /usr/lib/openvpn/plugins/openvpn-plugin-auth-pam.so login")
        lines.append("verify-client-cert none")
        lines.append("username-as-common-name")
        lines.append("")

        # --- Custom Server Config ---
        custom = settings.get("custom_server_config", "").strip()
        if custom:
            lines.append("# Custom Configuration (Admin Panel)")
            lines.append(custom)
            lines.append("")

        return "\n".join(lines)

    # ================================================================
    # PKI Management
    # ================================================================

    def _write_static_key(self, path: str):
        """Generate OpenVPN Static Key (2048 bit) using Python"""
        import secrets
        key_data = secrets.token_bytes(256)
        hex_data = key_data.hex()

        content = "-----BEGIN OpenVPN Static key V1-----\n"
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

            os.makedirs(self.DATA_DIR, exist_ok=True)

            # Remove old files
            for f in [self.CA_PATH, self.CA_KEY_PATH, self.TA_PATH]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception as rm_err:
                        logger.warning(f"Could not remove old file {f}: {rm_err}")

            # Generate CA cert + key
            subprocess.run(
                f"openssl req -new -x509 -days 3650 -nodes -text "
                f"-out {self.CA_PATH} -keyout {self.CA_KEY_PATH} "
                f"-subj '/CN=VPN-Master-Root-CA'",
                shell=True, check=True
            )

            # Generate TLS Auth/Crypt Key
            self._write_static_key(self.TA_PATH)

            # Generate DH parameters (if not exists)
            dh_path = os.path.join(self.DATA_DIR, "dh.pem")
            if not os.path.exists(dh_path):
                logger.info("Generating DH parameters (this may take a moment)...")
                subprocess.run(
                    f"openssl dhparam -out {dh_path} 2048",
                    shell=True, check=True
                )

            # Generate server cert + key
            server_key = os.path.join(self.DATA_DIR, "server.key")
            server_csr = os.path.join(self.DATA_DIR, "server.csr")
            server_cert = os.path.join(self.DATA_DIR, "server.crt")

            if not os.path.exists(server_cert):
                subprocess.run(
                    f"openssl req -new -nodes -keyout {server_key} "
                    f"-out {server_csr} -subj '/CN=VPN-Master-Server'",
                    shell=True, check=True
                )
                subprocess.run(
                    f"openssl x509 -req -days 3650 -in {server_csr} "
                    f"-CA {self.CA_PATH} -CAkey {self.CA_KEY_PATH} "
                    f"-CAcreateserial -out {server_cert}",
                    shell=True, check=True
                )

            logger.info("✅ OpenVPN PKI regenerated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to regenerate PKI: {e}")
            raise e

    def get_ca_info(self) -> Dict[str, Any]:
        """Get CA certificate information"""
        if not os.path.exists(self.CA_PATH):
            return {"exists": False}

        try:
            import subprocess
            result = subprocess.run(
                f"openssl x509 -in {self.CA_PATH} -noout -subject -dates -serial",
                shell=True, capture_output=True, text=True
            )
            output = result.stdout.strip()
            info = {"exists": True, "raw": output}

            for line in output.split("\n"):
                if line.startswith("subject="):
                    info["subject"] = line.replace("subject=", "").strip()
                elif line.startswith("notBefore="):
                    info["not_before"] = line.replace("notBefore=", "").strip()
                elif line.startswith("notAfter="):
                    info["not_after"] = line.replace("notAfter=", "").strip()
                elif line.startswith("serial="):
                    info["serial"] = line.replace("serial=", "").strip()

            return info
        except Exception as e:
            return {"exists": True, "error": str(e)}


# Singleton
openvpn_service = OpenVPNService()
