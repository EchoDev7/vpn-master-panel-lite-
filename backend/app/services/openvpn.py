"""
OpenVPN Service - World Class Configuration Generator (Phase 6)
Strictly adheres to OpenVPN 2.6 Reference Manual.
Supports:
- Advanced Network Topology ('subnet')
- Modern Cryptography (ECDHE, AES-GCM, CHACHA20)
- TLS Control Channel Security (tls-crypt/tls-crypt-v2)
- Anti-Censorship (Scramble, Fragment, MSSFix)
- Dynamic Push Options (Routes, DNS)
- Management Interface & Logging Control
"""
import os
import logging
import secrets
import subprocess
from typing import Optional, Dict, Any, List

# Cryptography imports
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

class OpenVPNService:
    """
    OpenVPN Configuration Manager
    Generates 'server.conf' and 'client.ovpn' based on comprehensive settings.
    """

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, "data", "openvpn")
    
    # Standard PKI Paths (managed by EasyRSA)
    CA_PATH = os.path.join(DATA_DIR, "ca.crt")
    SERVER_CERT = os.path.join(DATA_DIR, "server.crt")
    SERVER_KEY = os.path.join(DATA_DIR, "server.key")
    TA_KEY = os.path.join(DATA_DIR, "ta.key")
    CRL_PATH = os.path.join(DATA_DIR, "crl.pem")
    DH_PATH = os.path.join(DATA_DIR, "dh.pem") 

    def __init__(self):
        self._ensure_dirs()

    def _ensure_dirs(self):
        os.makedirs(self.DATA_DIR, exist_ok=True)
        # Log directory handling handled by systemd usually, but we ensure it exists
        try:
            os.makedirs("/var/log/openvpn", exist_ok=True)
        except PermissionError:
            logger.warning("Could not create /var/log/openvpn (Permission Denied). Logs might fail.")

    # ================================================================
    # Settings & Validation
    # ================================================================

    def _load_settings(self) -> Dict[str, str]:
        """Load settings from DB and merge with internal defaults if needed"""
        # Note: In a real app, you might cache this.
        from ..database import get_db_context
        from ..models.setting import Setting
        
        # We start with minimal defaults to ensure basic keys exist
        settings = {
            "protocol": "tcp", "port": "443", "server_subnet": "10.8.0.0",
            "server_netmask": "255.255.255.0", "dev": "tun", "topology": "subnet"
        }

        with get_db_context() as db:
            all_settings = db.query(Setting).all()
            for s in all_settings:
                if s.key.startswith("ovpn_"):
                    # key="ovpn_port" -> "port"
                    key = s.key.replace("ovpn_", "", 1)
                    settings[key] = s.value
        return settings

    def validate_config(self, settings: Dict[str, str]) -> List[str]:
        """
        Validate settings for logical consistency and security.
        Returns a list of warning messages.
        """
        warnings = []
        
        # 1. Topology Check
        if settings.get("topology") == "net30":
            warnings.append("Topology 'net30' is deprecated. Consider using 'subnet'.")

        # 2. Cipher Security
        weak_ciphers = ["BF-CBC", "DES-CBC", "RC4"]
        data_ciphers = settings.get("data_ciphers", "").upper()
        for weak in weak_ciphers:
            if weak in data_ciphers:
                warnings.append(f"Security Warning: Weak cipher '{weak}' detected in data_ciphers.")

        # 3. Protocol Mismatch
        if settings.get("explicit_exit_notify") == "1" and "tcp" in settings.get("protocol", ""):
             # explicit-exit-notify is UDP only in some versions, but 2.6 supports it for some cases. 
             # Safe validation: OpenVPN warns if used with TCP.
             pass

        # 4. Scramble Check
        if settings.get("scramble") == "1" and not settings.get("scramble_password"):
            warnings.append("Scramble is enabled but no password set. It will be ignored.")

        return warnings

    # ================================================================
    # Server Config Generation
    # ================================================================

    def generate_server_config(self) -> str:
        """Generate the complete server.conf string"""
        s = self._load_settings()
        conf = []

        # --- Header ---
        conf.append("# OpenVPN Server Configuration - Auto Generated")
        conf.append(f"# Created: {subprocess.check_output(['date']).decode().strip()}")
        conf.append("")

        # --- Network (Layer 1-3) ---
        conf.append("# --- Network ---")
        conf.append(f"port {s.get('port', '443')}")
        conf.append(f"proto {s.get('protocol', 'tcp')}")
        conf.append(f"dev {s.get('dev', 'tun')}")
        conf.append(f"dev-type {s.get('dev_type', 'tun')}")
        
        # Topology
        topo = s.get("topology", "subnet")
        conf.append(f"topology {topo}")
        conf.append(f"server {s.get('server_subnet', '10.8.0.0')} {s.get('server_netmask', '255.255.255.0')}")
        
        if s.get("max_clients"):
            conf.append(f"max-clients {s['max_clients']}")

        # --- PKI & Cryptography ---
        conf.append("\n# --- PKI & Cryptography ---")
        conf.append(f"ca {self.CA_PATH}")
        conf.append(f"cert {self.SERVER_CERT}")
        conf.append(f"key {self.SERVER_KEY}")
        
        # DH Parameters
        if s.get("dh_file") == "none":
            conf.append("dh none")
        elif os.path.exists(self.DH_PATH):
             conf.append(f"dh {self.DH_PATH}")
        else:
             conf.append("dh none") # Fallback to ECDH
             
        # ECDH Curve
        if s.get("ecdh_curve"):
            conf.append(f"ecdh-curve {s['ecdh_curve']}")

        # CRL
        if s.get("crl_verify") and os.path.exists(os.path.join(self.DATA_DIR, s['crl_verify'])):
            conf.append(f"crl-verify {os.path.join(self.DATA_DIR, s['crl_verify'])}")

        # TLS Control Channel
        tls_mode = s.get("tls_control_channel", "tls-crypt")
        if tls_mode == "tls-crypt":
            conf.append(f"tls-crypt {self.TA_KEY}")
        elif tls_mode == "tls-auth":
            conf.append(f"tls-auth {self.TA_KEY} 0")
        elif tls_mode == "tls-crypt-v2":
            # Requires server key specifically
            conf.append(f"tls-crypt-v2 {self.TA_KEY}") 
        elif tls_mode == "none":
            # Explicitly disabled
            pass

        # Auth & Ciphers
        auth_digest = s.get('auth_digest', 'SHA256')
        if auth_digest == 'none':
            conf.append("auth none") 
        else:
            conf.append(f"auth {auth_digest}")

        data_ciphers = s.get('data_ciphers', 'AES-256-GCM:AES-128-GCM')
        if data_ciphers == 'none':
             conf.append("data-ciphers none")
             conf.append("cipher none") # Legacy compatibility
        else:
            conf.append(f"data-ciphers {data_ciphers}")
            conf.append(f"data-ciphers-fallback {s.get('data_ciphers_fallback', 'AES-256-GCM')}")

        conf.append(f"tls-version-min {s.get('tls_version_min', '1.2')}")
        
        if s.get("tls_ciphers"):
            conf.append(f"tls-cipher {s['tls_ciphers']}")
        if s.get("tls_cipher_suites"):
            conf.append(f"tls-ciphersuites {s['tls_cipher_suites']}")
            
        conf.append(f"reneg-sec {s.get('reneg_sec', '3600')}")
        
        if s.get("auth_nocache") == "1":
            conf.append("auth-nocache")

        # --- Connection Reliability ---
        conf.append("\n# --- Reliability ---")
        conf.append(f"keepalive {s.get('keepalive_interval', '10')} {s.get('keepalive_timeout', '60')}")
        
        if s.get("duplicate_cn") == "1":
            conf.append("duplicate-cn")
            
        if s.get("explicit_exit_notify", "0") != "0" and "udp" in s.get("protocol", ""):
             conf.append(f"explicit-exit-notify {s['explicit_exit_notify']}")

        # Compression
        compress = s.get("compress", "")
        if compress:
            conf.append(f"compress {compress}")
        elif s.get("comp_lzo") == "yes":
            conf.append("comp-lzo") # Legacy
            
        if s.get("allow_compression") == "yes":
            conf.append("allow-compression yes")

        # --- Anti-Censorship ---
        conf.append("\n# --- Anti-Censorship ---")
        if s.get("scramble") == "1" and s.get("scramble_password"):
            conf.append(f'scramble obfuscate "{s["scramble_password"]}"')
            
        if s.get("fragment", "0") != "0":
            conf.append(f"fragment {s['fragment']}")
            conf.append(f"mssfix {s['fragment']}")
        else:
             # MSSFix is standard
             if s.get("mssfix"):
                 conf.append(f"mssfix {s['mssfix']}")
        
        if s.get("tun_mtu"):
            conf.append(f"tun-mtu {s['tun_mtu']}")

        # --- System & Logging ---
        conf.append("\n# --- System ---")
        conf.append(f"user {s.get('user', 'nobody')}")
        conf.append(f"group {s.get('group', 'nogroup')}")
        if s.get('pers_key', '1') == '1':
            conf.append("persist-key")
        if s.get('pers_tun', '1') == '1':
            conf.append("persist-tun")
        
        conf.append(f"verb {s.get('verb', '3')}")
        if s.get("mute"):
            conf.append(f"mute {s['mute']}")
            
        # Status Log
        conf.append(f"status {s.get('status_log', '/var/log/openvpn/openvpn-status.log')}")
        conf.append(f"status-version {s.get('status_version', '2')}")
        
        # Management Interface
        mgmt = s.get("management")
        if mgmt:
             conf.append(f"management {mgmt}")

        # IP Pool Persistence
        conf.append("ifconfig-pool-persist /var/log/openvpn/ipp.txt")

        # --- Pushed Options ---
        conf.append("\n# --- Push Options ---")
        # Gateway
        if s.get("redirect_gateway") == "1":
            conf.append('push "redirect-gateway def1 bypass-dhcp"')
            
        # DNS
        dns_list = s.get("dns", "").replace(",", " ").split()
        for dns in dns_list:
            if dns.strip():
                conf.append(f'push "dhcp-option DNS {dns.strip()}"')
                
        if s.get("block_outside_dns") == "1":
            conf.append('push "block-outside-dns"')
            
        # Routes
        routes = s.get("push_routes", "").split(",")
        for route in routes:
            if route.strip():
                conf.append(f'push "route {route.strip()}"')

        # --- Authentication ---
        conf.append("\n# --- Authentication ---")
        
        # Resolve Authentication Mode
        # options: 'password' (default), 'cert', '2fa'
        auth_mode = s.get("auth_mode", "password")
        
        pam_plugin = self._find_pam_plugin()
        if not pam_plugin and auth_mode in ["password", "2fa"]:
             logger.error("PAM Plugin not found! Falling back to Certificate Authentication.")
             auth_mode = "cert"

        if auth_mode == "password":
            # Use custom python script for DB auth instead of PAM
            auth_script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "auth.py")
            if os.path.exists(auth_script):
                conf.append("script-security 3")
                conf.append(f"auth-user-pass-verify {auth_script} via-file")
                conf.append("username-as-common-name")
                conf.append("verify-client-cert none")
            elif pam_plugin:
                conf.append(f"plugin {pam_plugin} login") # Fallback to PAM if script missing
                conf.append("username-as-common-name")
                conf.append("verify-client-cert none")
            else:
                conf.append("# PAM Plugin missing - Fallback to Cert Only")
                conf.append("verify-client-cert require")
                
        elif auth_mode == "2fa":
            # Cert + Password
            if pam_plugin:
                conf.append(f"plugin {pam_plugin} login")
            conf.append("verify-client-cert require")
            
        else: # cert or none
            conf.append("verify-client-cert require")

        # --- Custom Config ---
        custom = s.get("custom_server_config")
        if custom:
            conf.append("\n# --- Custom Config ---")
            conf.append(custom)

        return "\n".join([line for line in conf if line.strip() != ""])

    # ================================================================
    # Client Config Generation
    # ================================================================

    def generate_client_config(
        self,
        username: str,
        password: str = None, # Not used in config, but for context
        server_ip_override: str = None,
        port_override: int = None,
        protocol_override: str = None
    ) -> str:
        """Generate .ovpn client configuration"""
        self._ensure_pki() # Verify files exist
        
        s = self._load_settings()
        conf = []

        # Resolving Connection Details
        remote_ip = server_ip_override or s.get("server_ip") or self._get_public_ip()
        remote_port = str(port_override) if port_override else s.get("port", "443")
        remote_proto = protocol_override or s.get("protocol", "tcp")
        # Client config uses 'tcp-client' or 'udp' typically, but 'tcp' alias works
        if remote_proto == "both": remote_proto = "tcp"

        conf.append(f"# OpenVPN Config for {username}")
        conf.append("client")
        conf.append(f"dev {s.get('dev', 'tun')}")
        conf.append(f"proto {remote_proto}")
        
        # Remotes
        remotes = s.get("remote_servers", "").split(",")
        has_remotes = False
        for r in remotes:
            if r.strip():
                # Format: ip:port:proto
                parts = r.strip().split(":")
                if len(parts) >= 2:
                     ip, port = parts[0], parts[1]
                     proto = parts[2] if len(parts) > 2 else remote_proto
                     conf.append(f"remote {ip} {port} {proto}")
                     has_remotes = True
        
        # Add primary remote
        conf.append(f"remote {remote_ip} {remote_port}")
        
        if has_remotes:
            conf.append("remote-random")
            conf.append("resolv-retry infinite")

        conf.append("nobind")
        
        # Security
        conf.append("remote-cert-tls server")
        conf.append(f"auth {s.get('auth_digest', 'SHA256')}")
        conf.append(f"data-ciphers {s.get('data_ciphers', 'AES-256-GCM:AES-128-GCM')}")
        # Note: older clients might need 'cipher' directive, but we focus on modern.
        # Adding fallback for compatibility:
        conf.append(f"cipher {s.get('data_ciphers_fallback', 'AES-256-GCM')}") 
        
        conf.append(f"tls-version-min {s.get('tls_version_min', '1.2')}")
        
        # Compression
        compress = s.get("compress", "")
        if compress:
            conf.append(f"compress {compress}")
        elif s.get("comp_lzo") == "yes":
            conf.append("comp-lzo")

        conf.append(f"verb {s.get('verb', '3')}")

        # Anti-Censorship
        if s.get("scramble") == "1" and s.get("scramble_password"):
             conf.append(f'scramble obfuscate "{s["scramble_password"]}"')
        
        if s.get("fragment", "0") != "0":
            conf.append(f"fragment {s['fragment']}")
            conf.append(f"mssfix {s['fragment']}")
        else:
            if s.get("mssfix"):
                conf.append(f"mssfix {s['mssfix']}")

        # Auth
        conf.append("auth-user-pass")
        
        # Proxy
        p_type = s.get("proxy_type", "none")
        if p_type != "none":
            addr = s.get("proxy_address")
            prt = s.get("proxy_port")
            if addr and prt:
                conf.append(f"{p_type}-proxy {addr} {prt}")

        # Keys
        conf.append("\n<ca>")
        conf.append(self._read_file(self.CA_PATH))
        conf.append("</ca>")

        tls_mode = s.get("tls_control_channel", "tls-crypt")
        if tls_mode != "none":
            ta_content = self._read_file(self.TA_KEY)
            if "BEGIN" in ta_content:
                if tls_mode == "tls-auth":
                    conf.append("key-direction 1")
                    conf.append("<tls-auth>")
                    conf.append(ta_content)
                    conf.append("</tls-auth>")
                else:
                    # tls-crypt and tls-crypt-v2
                    conf.append("<tls-crypt>")
                    conf.append(ta_content)
                    conf.append("</tls-crypt>")

        # Custom
        if s.get("custom_client_config"):
            conf.append(s["custom_client_config"])

        return "\n".join(conf)

    # ================================================================
    # Internal Helpers
    # ================================================================

    def _get_public_ip(self) -> str:
        """Resolve public IP"""
        # (Similar logic to previous implementation, simplified)
        try:
             import requests
             return requests.get('https://api.ipify.org', timeout=2).text.strip()
        except:
             return "YOUR_SERVER_IP"

    def _read_file(self, path: str) -> str:
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
        return f"# MISSING: {path}"

    def _ensure_pki(self):
        """Minimal check for PKI existence"""
        missing = []
        for f in [self.CA_PATH, self.SERVER_CERT, self.SERVER_KEY, self.TA_KEY]:
            if not os.path.exists(f):
                missing.append(os.path.basename(f))
        
        if missing:
            logger.warning(f"Missing PKI files: {missing}. Service may fail.")
            # We don't raise here to allow Admin to see error in UI logs
    
    def get_ca_info(self) -> Dict[str, Any]:
        """Info for UI"""
        if not os.path.exists(self.CA_PATH): return {"exists": False}
        try:
            with open(self.CA_PATH, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read(), default_backend())
            return {
                "exists": True,
                "subject": cert.subject.rfc4514_string(),
                "not_after": cert.not_valid_after.strftime("%Y-%m-%d")
            }
        except:
            return {"exists": True, "error": "Invalid Cert"}
            
    # Legacy Shim
    def regenerate_pki(self):
        """
        Regenerate all OpenVPN certificates and keys using OpenSSL.
        This fixes 'key values mismatch' errors by creating a fresh, matching set.
        """
        logger.info("Starting PKI Regeneration...")
        try:
            # 1. Clean old files
            for f in [self.CA_PATH, self.SERVER_CERT, self.SERVER_KEY, self.TA_KEY, self.DH_PATH, self.CRL_PATH]:
                if os.path.exists(f):
                    os.remove(f)

            # 2. Generate CA
            # openssl req -new -x509 -days 3650 -nodes -out ca.crt -keyout ca.key -subj "/CN=VPN-Master-CA"
            subprocess.run([
                "openssl", "req", "-new", "-x509", "-days", "3650", "-nodes",
                "-out", self.CA_PATH,
                "-keyout", os.path.join(self.DATA_DIR, "ca.key"),
                "-subj", "/CN=VPN-Master-CA"
            ], check=True)

            # 3. Generate Server Key & CSR
            # openssl req -new -nodes -out server.csr -keyout server.key -subj "/CN=server"
            server_csr = os.path.join(self.DATA_DIR, "server.csr")
            subprocess.run([
                "openssl", "req", "-new", "-nodes",
                "-out", server_csr,
                "-keyout", self.SERVER_KEY,
                "-subj", "/CN=server"
            ], check=True)

            # 3.5 Create Extensions File for Server Cert (Critical for mobile clients)
            # Modern clients require extendedKeyUsage=serverAuth to satisfy 'remote-cert-tls server'
            ext_path = os.path.join(self.DATA_DIR, "server.ext")
            with open(ext_path, "w") as f:
                f.write("basicConstraints=CA:FALSE\n")
                f.write("nsCertType=server\n")
                f.write("keyUsage=digitalSignature,keyEncipherment\n")
                f.write("extendedKeyUsage=serverAuth\n")
                f.write("subjectKeyIdentifier=hash\n")
                f.write("authorityKeyIdentifier=keyid,issuer\n")

            # 4. Sign Server CSR with CA and Extensions
            # openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 3650 -extfile server.ext
            subprocess.run([
                "openssl", "x509", "-req",
                "-in", server_csr,
                "-CA", self.CA_PATH,
                "-CAkey", os.path.join(self.DATA_DIR, "ca.key"),
                "-CAcreateserial",
                "-out", self.SERVER_CERT,
                "-days", "3650",
                "-extfile", ext_path
            ], check=True)

            # 5. Generate Diffie-Hellman (DH)
            # openssl dhparam -out dh.pem 2048
            subprocess.run(["openssl", "dhparam", "-out", self.DH_PATH, "2048"], check=True)

            # 6. Generate TLS-Auth Key (TA)
            # openvpn --genkey secret ta.key
            subprocess.run(["openvpn", "--genkey", "secret", self.TA_KEY], check=True)

            # 7. Set Permissions (Security Fix)
            # chmod 600 server.key ta.key ca.key
            subprocess.run(["chmod", "600", self.SERVER_KEY, self.TA_KEY, os.path.join(self.DATA_DIR, "ca.key")], check=True)

            # Cleanup CSR
            if os.path.exists(server_csr):
                os.remove(server_csr)

            logger.info("PKI Regeneration Complete.")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"PKI Regeneration Failed: {e}")
            raise e

    def _find_pam_plugin(self) -> Optional[str]:
        """Locate openvpn-plugin-auth-pam.so in common paths"""
        candidates = [
            "/usr/lib/openvpn/plugins/openvpn-plugin-auth-pam.so",
            "/usr/lib/x86_64-linux-gnu/openvpn/plugins/openvpn-plugin-auth-pam.so",
            "/usr/lib64/openvpn/plugins/openvpn-plugin-auth-pam.so",
            "/usr/local/lib/openvpn/plugins/openvpn-plugin-auth-pam.so",
            "/usr/lib/openvpn/openvpn-plugin-auth-pam.so"
        ]
        
        # Check environment override first if implemented (future)
        # Check filesystem
        for path in candidates:
            if os.path.exists(path):
                return path
        
        return None

openvpn_service = OpenVPNService()
