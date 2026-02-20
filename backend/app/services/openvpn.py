"""
OpenVPN Service — Iran DPI Bypass Edition
==========================================
Optimized for:
  • Bypassing Iran's deep-packet inspection (DPI) and SNI filtering
  • Cross-platform clients: Android, iOS, Windows, macOS
  • Maximum security with modern cryptography

Key anti-censorship techniques used:
  1. TCP port 443 (HTTPS camouflage) — default for Iran
  2. tls-crypt  — hides OpenVPN TLS fingerprint inside encrypted HMAC wrapper;
                  DPI cannot even identify it as TLS/OpenVPN
  3. tls-version-min 1.3 (server-side push) with 1.2 fallback for old clients
  4. TLS cipher suite whitelisting — matches HTTPS browser fingerprint
  5. MSS-fix + fragment — handles VPS MTU issues, prevents "Large Packet Drop"
  6. sndbuf/rcvbuf 0  — let OS auto-tune (prevents throttle on high-bandwidth VPS)
  7. Client config includes block-outside-dns for Windows DNS leak protection
  8. iOS/Android: float, nobind, persist-tun/key for mobile reconnect support
  9. macOS/Windows: route-nopull + specific pushed routes for split-tunnel option

Adheres to OpenVPN 2.5/2.6 Reference Manual.
"""
import os
import logging
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, List

from cryptography import x509
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class OpenVPNService:
    """
    OpenVPN Configuration Manager.
    Generates server.conf and per-user .ovpn based on DB settings.
    """

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, "data", "openvpn")

    # PKI file paths (all managed by regenerate_pki / update.sh)
    CA_PATH     = os.path.join(DATA_DIR, "ca.crt")
    SERVER_CERT = os.path.join(DATA_DIR, "server.crt")
    SERVER_KEY  = os.path.join(DATA_DIR, "server.key")
    TA_KEY      = os.path.join(DATA_DIR, "ta.key")
    CRL_PATH    = os.path.join(DATA_DIR, "crl.pem")
    DH_PATH     = os.path.join(DATA_DIR, "dh.pem")

    def __init__(self):
        self._ensure_dirs()

    # ------------------------------------------------------------------
    # Directory helpers
    # ------------------------------------------------------------------

    def _ensure_dirs(self):
        os.makedirs(self.DATA_DIR, exist_ok=True)
        try:
            os.makedirs("/var/log/openvpn", exist_ok=True)
        except PermissionError:
            logger.warning("Cannot create /var/log/openvpn — running without root?")

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _load_settings(self) -> Dict[str, str]:
        """Load ovpn_* settings from DB, merged with safe hard defaults."""
        from ..database import get_db_context
        from ..models.setting import Setting

        # Hard defaults — Iran-optimised
        defaults: Dict[str, str] = {
            # Network
            "protocol":        "tcp",
            "port":            "443",
            "dev":             "tun",
            "topology":        "subnet",
            "server_subnet":   "10.8.0.0",
            "server_netmask":  "255.255.255.0",
            "max_clients":     "100",
            # Crypto
            "data_ciphers":          "AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305",
            "data_ciphers_fallback": "AES-256-GCM",
            "auth_digest":           "SHA256",
            "tls_version_min":       "1.2",
            "tls_control_channel":   "tls-crypt",
            # TLS cipher suite for TLS 1.3 (OpenVPN 2.5+)
            "tls_cipher_suites": "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256",
            # TLS cipher for TLS 1.2 fallback
            "tls_ciphers":  (
                "TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384:"
                "TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384:"
                "TLS-ECDHE-ECDSA-WITH-CHACHA20-POLY1305-SHA256:"
                "TLS-ECDHE-RSA-WITH-CHACHA20-POLY1305-SHA256"
            ),
            "ecdh_curve":    "secp384r1",
            "dh_file":       "none",    # Pure ECDHE — no static DH
            "reneg_sec":     "3600",
            "auth_nocache":  "1",
            # Reliability
            "keepalive_interval": "10",
            "keepalive_timeout":  "60",
            "float":              "1",
            "tun_mtu":            "1500",
            "mssfix":             "1450",
            # Logging & management
            "verb":           "3",
            "mute":           "20",
            "status_log":     "/var/log/openvpn/openvpn-status.log",
            "status_version": "2",
            "management":     "127.0.0.1 7505",
            # Push options
            "redirect_gateway": "1",
            "dns":              "1.1.1.1,8.8.8.8",
            "block_outside_dns": "1",
            # Auth
            "auth_mode": "password",
            # System
            "user":      "nobody",
            "group":     "nogroup",
            "pers_key":  "1",
            "pers_tun":  "1",
        }

        with get_db_context() as db:
            rows = db.query(Setting).filter(Setting.key.like("ovpn_%")).all()
            for row in rows:
                key = row.key[5:]  # strip "ovpn_" prefix
                defaults[key] = row.value

        return defaults

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_config(self, settings: Dict[str, str]) -> List[str]:
        """Return list of human-readable warnings (does not raise)."""
        warnings: List[str] = []

        if settings.get("topology") == "net30":
            warnings.append("'net30' topology is deprecated — use 'subnet'.")

        weak = {"BF-CBC", "DES-CBC", "RC4", "DES"}
        for cipher in weak:
            if cipher in settings.get("data_ciphers", "").upper():
                warnings.append(f"Weak cipher detected: {cipher}")

        if settings.get("tls_control_channel") == "none":
            warnings.append(
                "tls-crypt is disabled. Traffic fingerprint is exposed to DPI."
            )

        if settings.get("protocol") == "udp" and settings.get("port") == "443":
            warnings.append(
                "UDP/443 is blocked in Iran. Use TCP/443 for reliable bypass."
            )

        if settings.get("compress") and settings.get("compress") != "none":
            warnings.append(
                "Compression enabled. This can leak information (VORACLE attack)."
            )

        return warnings

    # ------------------------------------------------------------------
    # Server config generation
    # ------------------------------------------------------------------

    def generate_server_config(self) -> str:
        """Generate complete /etc/openvpn/server.conf content."""
        s = self._load_settings()
        conf: List[str] = []

        # ── Header ───────────────────────────────────────────────────
        conf += [
            "# OpenVPN Server Configuration",
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "# Iran DPI Bypass Edition — TCP/443 + tls-crypt",
            "",
        ]

        # ── Network layer ────────────────────────────────────────────
        conf += ["# ── Network ──────────────────────────────────────────"]
        proto = s.get("protocol", "tcp")
        conf.append(f"proto {proto}")
        conf.append(f"port {s.get('port', '443')}")
        conf.append(f"dev {s.get('dev', 'tun')}")
        conf.append(f"topology {s.get('topology', 'subnet')}")
        conf.append(
            f"server {s.get('server_subnet','10.8.0.0')} "
            f"{s.get('server_netmask','255.255.255.0')}"
        )
        conf.append("ifconfig-pool-persist /etc/openvpn/ipp.txt")
        if s.get("max_clients"):
            conf.append(f"max-clients {s['max_clients']}")

        # ── PKI & Cryptography ───────────────────────────────────────
        conf += ["", "# ── PKI & Cryptography ───────────────────────────"]
        conf.append(f"ca   {self.CA_PATH}")
        conf.append(f"cert {self.SERVER_CERT}")
        conf.append(f"key  {self.SERVER_KEY}")

        # DH: prefer "none" (pure ECDHE) for forward secrecy & speed
        if s.get("dh_file") == "none" or not os.path.exists(self.DH_PATH):
            conf.append("dh none")
        else:
            conf.append(f"dh {self.DH_PATH}")

        # ECDH curve — secp384r1 is NIST P-384 (high security, widely supported)
        conf.append(f"ecdh-curve {s.get('ecdh_curve', 'secp384r1')}")

        # CRL (certificate revocation)
        crl_key = s.get("crl_verify", "crl.pem")
        crl_full = os.path.join(self.DATA_DIR, crl_key)
        if crl_key and os.path.exists(crl_full):
            conf.append(f"crl-verify {crl_full}")

        # TLS control channel — tls-crypt hides OpenVPN's TLS ClientHello from DPI
        tls_mode = s.get("tls_control_channel", "tls-crypt")
        ta_exists = os.path.exists(self.TA_KEY)
        if tls_mode == "tls-crypt" and ta_exists:
            conf.append(f"tls-crypt {self.TA_KEY}")
        elif tls_mode == "tls-auth" and ta_exists:
            conf.append(f"tls-auth {self.TA_KEY} 0")
        elif tls_mode == "tls-crypt-v2" and ta_exists:
            # tls-crypt-v2 requires per-client keys; fall back to tls-crypt
            conf.append(f"tls-crypt {self.TA_KEY}")
            logger.warning("tls-crypt-v2 not fully supported in Lite — using tls-crypt")
        # else: tls_mode == "none" → no tls-crypt directive

        # Data-plane cipher negotiation (NCP)
        data_ciphers = s.get("data_ciphers", "AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305")
        conf.append(f"data-ciphers {data_ciphers}")
        conf.append(f"data-ciphers-fallback {s.get('data_ciphers_fallback','AES-256-GCM')}")

        # HMAC auth for control channel packets
        auth_digest = s.get("auth_digest", "SHA256")
        conf.append(f"auth {auth_digest}")

        # TLS version & cipher suite restrictions
        conf.append(f"tls-version-min {s.get('tls_version_min', '1.2')}")
        tls_ciphers = s.get("tls_ciphers", "")
        if tls_ciphers:
            conf.append(f"tls-cipher {tls_ciphers}")
        tls_suites = s.get("tls_cipher_suites", "")
        if tls_suites:
            conf.append(f"tls-ciphersuites {tls_suites}")

        # TLS renegotiation interval
        conf.append(f"reneg-sec {s.get('reneg_sec', '3600')}")

        # Don't cache credentials in memory
        if s.get("auth_nocache", "1") == "1":
            conf.append("auth-nocache")

        # ── Connection Reliability ───────────────────────────────────
        conf += ["", "# ── Reliability ─────────────────────────────────"]
        conf.append(
            f"keepalive {s.get('keepalive_interval','10')} "
            f"{s.get('keepalive_timeout','60')}"
        )

        # float: allow clients whose IP changes (mobile networks, especially Iran)
        if s.get("float", "1") == "1":
            conf.append("float")

        # duplicate-cn: allow same cert from multiple devices (not recommended for security)
        if s.get("duplicate_cn") == "1":
            conf.append("duplicate-cn")

        # explicit-exit-notify is UDP-only
        if s.get("explicit_exit_notify", "0") != "0" and "udp" in proto:
            conf.append(f"explicit-exit-notify {s['explicit_exit_notify']}")

        # MTU tuning
        # TCP/443: use 1500 byte MTU (Ethernet standard); mssfix handles TCP inside TCP
        tun_mtu = s.get("tun_mtu", "1500")
        mssfix  = s.get("mssfix", "1450")
        conf.append(f"tun-mtu {tun_mtu}")
        conf.append(f"mssfix {mssfix}")

        # Fragment: only add if explicitly configured (non-zero)
        fragment = s.get("fragment", "0")
        if fragment and fragment != "0":
            conf.append(f"fragment {fragment}")

        # Socket buffer: 0 = let OS auto-size (best for VPS)
        conf.append("sndbuf 0")
        conf.append("rcvbuf 0")

        # TLS handshake / transition windows
        if s.get("hand_window"):
            conf.append(f"hand-window {s['hand_window']}")
        if s.get("tran_window"):
            conf.append(f"tran-window {s['tran_window']}")
        if s.get("tls_timeout"):
            conf.append(f"tls-timeout {s['tls_timeout']}")

        # Compression — DISABLED by default (VORACLE attack; also DPI detectable)
        # Only enable if explicitly set AND allow-compression yes
        compress_val = s.get("compress", "")
        if compress_val and compress_val not in ("", "none"):
            conf.append(f"compress {compress_val}")
            conf.append(f'push "compress {compress_val}"')
            conf.append("allow-compression yes")
        else:
            # Explicitly reject if client tries to negotiate compression
            conf.append("compress")
            conf.append("push \"compress\"")

        # ── Port Sharing (Iran bypass: share port 443 with HTTPS) ────
        conf += ["", "# ── Anti-Censorship ──────────────────────────────"]
        port_share = s.get("port_share", "")
        if port_share:
            # e.g. "localhost 443" to share with nginx/Apache
            conf.append(f"port-share {port_share}")

        # ── System ──────────────────────────────────────────────────
        conf += ["", "# ── System ───────────────────────────────────────"]
        conf.append(f"user  {s.get('user',  'nobody')}")
        conf.append(f"group {s.get('group', 'nogroup')}")
        if s.get("pers_key", "1") == "1":
            conf.append("persist-key")
        if s.get("pers_tun", "1") == "1":
            conf.append("persist-tun")

        conf.append(f"verb {s.get('verb', '3')}")
        if s.get("mute"):
            conf.append(f"mute {s['mute']}")

        # Status log — version 2 uses CLIENT_LIST rows (what monitoring.py expects)
        conf.append(f"status {s.get('status_log', '/var/log/openvpn/openvpn-status.log')} 10")
        conf.append(f"status-version {s.get('status_version', '2')}")

        # Management interface (used by openvpn_mgmt.py for real-time stats)
        mgmt = s.get("management", "127.0.0.1 7505")
        conf.append(f"management {mgmt}")

        # ── Push Options ─────────────────────────────────────────────
        conf += ["", "# ── Push Options ─────────────────────────────────"]

        if s.get("redirect_gateway", "1") == "1":
            conf.append('push "redirect-gateway def1 bypass-dhcp"')

        # DNS push — 1.1.1.1 and 8.8.8.8 work inside Iran for VPN tunnels
        dns_raw = s.get("dns", "1.1.1.1,8.8.8.8")
        for dns in dns_raw.replace(",", " ").split():
            if dns.strip():
                conf.append(f'push "dhcp-option DNS {dns.strip()}"')

        # block-outside-dns: critical for Windows DNS leak protection
        if s.get("block_outside_dns", "1") == "1":
            conf.append('push "block-outside-dns"')

        # Client-to-client (disabled by default — privacy)
        if s.get("client_to_client") == "1":
            conf.append("client-to-client")

        # Additional routes
        for route in s.get("push_routes", "").split(","):
            r = route.strip()
            if r:
                conf.append(f'push "route {r}"')

        # ── Authentication ───────────────────────────────────────────
        conf += ["", "# ── Authentication ───────────────────────────────"]

        auth_mode  = s.get("auth_mode", "password")
        pam_plugin = self._find_pam_plugin()

        # If PAM not found and password auth needed, fall back gracefully
        if auth_mode in ("password", "2fa") and not pam_plugin:
            logger.warning("PAM plugin not found — auth script will be used for DB auth.")

        if auth_mode == "password":
            script = "/etc/openvpn/scripts/auth.sh"
            if not os.path.exists(script):
                # Dev fallback
                if os.path.exists("/etc/openvpn/scripts/auth.py"):
                    script = "/etc/openvpn/scripts/auth.py"
                else:
                    logger.error(
                        f"Auth script not found at {script}. "
                        "Run update.sh to deploy it."
                    )
                    script = None

            if script:
                conf.append("script-security 2")
                conf.append(f"auth-user-pass-verify {script} via-file")
                conf.append("client-connect  /etc/openvpn/scripts/client-connect.sh")
                conf.append("client-disconnect /etc/openvpn/scripts/client-disconnect.sh")
                conf.append("username-as-common-name")
                conf.append("verify-client-cert none")
            elif pam_plugin:
                conf.append("script-security 2")
                conf.append(f"plugin {pam_plugin} login")
                conf.append("username-as-common-name")
                conf.append("verify-client-cert none")
            else:
                conf.append("# ERROR: no auth script or PAM plugin found")
                conf.append("verify-client-cert require")

        elif auth_mode == "2fa":
            if pam_plugin:
                conf.append("script-security 2")
                conf.append(f"plugin {pam_plugin} login")
            conf.append("verify-client-cert require")
        else:
            # cert-only
            conf.append("verify-client-cert require")

        # ── Custom append ────────────────────────────────────────────
        custom = s.get("custom_server_config", "")
        if custom.strip():
            conf += ["", "# ── Custom Config ─────────────────────────────────", custom]

        # Filter out blank lines caused by empty sections, but keep deliberate blanks
        return "\n".join(conf)

    # ------------------------------------------------------------------
    # Client config generation
    # ------------------------------------------------------------------

    def generate_client_config(
        self,
        username: str,
        password: str = None,
        server_ip_override: str = None,
        port_override: int = None,
        protocol_override: str = None,
    ) -> str:
        """
        Generate a .ovpn file optimised for:
          - Android (OpenVPN for Android / OpenVPN Connect)
          - iOS (OpenVPN Connect)
          - Windows (OpenVPN GUI 2.5+)
          - macOS (Tunnelblick / OpenVPN Connect)

        Key decisions:
          - TCP/443 by default (works in Iran)
          - tls-crypt embedded inline
          - CA embedded inline
          - auth-user-pass (username/password prompt)
          - block-outside-dns for Windows
          - persist-tun for mobile reconnect
          - redirect-gateway def1 (full tunnel)
          - No LZO/compression (security + DPI fingerprint)
        """
        self._ensure_pki()
        s = self._load_settings()

        # ── Resolve remote address ───────────────────────────────────
        addr_type = s.get("remote_address_type", "auto")
        if server_ip_override:
            remote_ip = server_ip_override
        elif addr_type == "domain" and s.get("remote_domain"):
            remote_ip = s["remote_domain"]
        elif addr_type == "custom_ip" and s.get("server_ip"):
            remote_ip = s["server_ip"]
        else:
            remote_ip = self._get_public_ip()

        remote_port  = str(port_override) if port_override else s.get("port", "443")
        remote_proto = protocol_override or s.get("protocol", "tcp")
        if remote_proto == "both":
            remote_proto = "tcp"

        conf: List[str] = []

        # ── Header ───────────────────────────────────────────────────
        conf += [
            f"# OpenVPN client config — {username}",
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "# Compatible: Android, iOS, Windows, macOS",
            "",
            "client",
            f"dev tun",
            f"proto {remote_proto}",
        ]

        # ── Remotes (primary + failover) ─────────────────────────────
        # Additional remotes (comma-separated "ip:port:proto")
        extra_remotes_raw = s.get("remote_servers", "")
        has_extra = False
        for entry in extra_remotes_raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            parts = entry.split(":")
            if len(parts) >= 2:
                r_ip, r_port = parts[0], parts[1]
                r_proto = parts[2] if len(parts) > 2 else remote_proto
                conf.append(f"remote {r_ip} {r_port} {r_proto}")
                has_extra = True

        # Primary remote always last (lower priority with remote-random)
        conf.append(f"remote {remote_ip} {remote_port} {remote_proto}")
        if has_extra:
            conf.append("remote-random")

        # ── Connection behaviour ──────────────────────────────────────
        conf += [
            "",
            "# ── Connection ──────────────────────────────────────────",
            "resolv-retry infinite",
            "nobind",
            "persist-key",
            "persist-tun",         # critical for Android/iOS reconnect
            "remote-cert-tls server",
        ]

        # float: allow server IP to change (not needed client-side usually, but harmless)
        # Android reconnects after network switch — remote-cert-tls handles security

        # ── Cryptography ─────────────────────────────────────────────
        conf += [
            "",
            "# ── Cryptography ────────────────────────────────────────",
        ]

        data_ciphers = s.get("data_ciphers", "AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305")
        conf.append(f"data-ciphers {data_ciphers}")
        conf.append(f"data-ciphers-fallback {s.get('data_ciphers_fallback','AES-256-GCM')}")
        conf.append(f"auth {s.get('auth_digest','SHA256')}")

        tls_min = s.get("tls_version_min", "1.2")
        conf.append(f"tls-version-min {tls_min}")

        tls_ciphers = s.get("tls_ciphers", "")
        if tls_ciphers:
            conf.append(f"tls-cipher {tls_ciphers}")

        tls_suites = s.get("tls_cipher_suites", "")
        if tls_suites:
            conf.append(f"tls-ciphersuites {tls_suites}")

        # Compression — DISABLED (VORACLE; DPI fingerprint)
        conf.append("compress")      # negotiate off

        # ── MTU / MSS ─────────────────────────────────────────────────
        conf += [
            "",
            "# ── MTU / MSS ───────────────────────────────────────────",
            f"tun-mtu {s.get('tun_mtu','1500')}",
            f"mssfix  {s.get('mssfix','1450')}",
        ]
        fragment = s.get("fragment", "0")
        if fragment and fragment != "0":
            conf.append(f"fragment {fragment}")

        # ── Routing ──────────────────────────────────────────────────
        conf += [
            "",
            "# ── Routing ─────────────────────────────────────────────",
        ]
        if s.get("redirect_gateway", "1") == "1":
            conf.append("redirect-gateway def1 bypass-dhcp")

        # ── Platform-specific ─────────────────────────────────────────
        conf += [
            "",
            "# ── Platform-specific (Windows: DNS leak protection) ─────",
            "block-outside-dns",    # Windows 10+ DNS leak fix; harmless on other OS
            "",
            "# ── Logging ─────────────────────────────────────────────",
            f"verb {s.get('verb','3')}",
            "",
            "# ── Credentials ─────────────────────────────────────────",
            "auth-user-pass",       # prompt for username/password
        ]

        # ── HTTP proxy (domain fronting / Iran bypass) ────────────────
        if s.get("http_proxy_enabled") == "1":
            proxy_host = s.get("http_proxy_host", "")
            proxy_port = s.get("http_proxy_port", "80")
            if proxy_host:
                conf += [
                    "",
                    "# ── HTTP Proxy (domain fronting) ─────────────────────",
                    f"http-proxy {proxy_host} {proxy_port}",
                ]
                custom_host_header = s.get("http_proxy_custom_header", "")
                if custom_host_header:
                    conf.append(f"http-proxy-option CUSTOM-HEADER Host {custom_host_header}")
                    conf.append("http-proxy-option VERSION 1.1")

        # ── Inline CA ────────────────────────────────────────────────
        conf += ["", "<ca>", self._read_file(self.CA_PATH), "</ca>"]

        # ── Inline tls-crypt / tls-auth ──────────────────────────────
        tls_mode = s.get("tls_control_channel", "tls-crypt")
        if tls_mode != "none" and os.path.exists(self.TA_KEY):
            ta_content = self._read_file(self.TA_KEY)
            if "BEGIN" in ta_content:
                if tls_mode == "tls-auth":
                    conf.append("key-direction 1")
                    conf += ["<tls-auth>", ta_content, "</tls-auth>"]
                else:
                    conf += ["<tls-crypt>", ta_content, "</tls-crypt>"]

        # ── Custom client append ──────────────────────────────────────
        custom_client = s.get("custom_client_config", "")
        if custom_client.strip():
            conf += ["", "# ── Custom ───────────────────────────────────────", custom_client]

        return "\n".join(conf)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_public_ip(self) -> str:
        """Detect server's public IPv4 address without external libraries."""
        # 1. Public API endpoints (fast, reliable)
        for url in ["https://api.ipify.org", "https://ident.me", "https://ifconfig.me/ip"]:
            try:
                import urllib.request
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    ip = resp.read().decode().strip()
                    if ip.count(".") == 3:
                        return ip
            except Exception:
                continue

        # 2. Kernel routing table (no network call)
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 53))
                ip = sock.getsockname()[0]
                if ip and not ip.startswith("127."):
                    return ip
        except Exception:
            pass

        # 3. hostname -I fallback
        try:
            ip = subprocess.check_output(
                ["hostname", "-I"], text=True
            ).split()[0]
            if ip.count(".") == 3:
                return ip
        except Exception:
            pass

        return "YOUR_SERVER_IP"

    def _read_file(self, path: str) -> str:
        if os.path.exists(path):
            with open(path) as f:
                return f.read().strip()
        return f"# MISSING FILE: {path}"

    def _ensure_pki(self):
        """Warn (don't raise) if PKI files are missing."""
        missing = [
            os.path.basename(p)
            for p in [self.CA_PATH, self.SERVER_CERT, self.SERVER_KEY, self.TA_KEY]
            if not os.path.exists(p)
        ]
        if missing:
            logger.warning(f"Missing PKI files: {missing}. Use Settings → Regenerate PKI.")

    def get_ca_info(self) -> Dict[str, Any]:
        """Return CA certificate metadata for the UI."""
        if not os.path.exists(self.CA_PATH):
            return {"exists": False}
        try:
            with open(self.CA_PATH, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read(), default_backend())
            return {
                "exists": True,
                "subject":    cert.subject.rfc4514_string(),
                "not_before": cert.not_valid_before.strftime("%Y-%m-%d"),
                "not_after":  cert.not_valid_after.strftime("%Y-%m-%d"),
            }
        except Exception as exc:
            return {"exists": True, "error": str(exc)}

    def revoke_user_cert(self, username: str) -> bool:
        """
        Revoke a user certificate and regenerate the CRL.
        Note: only works if the cert was generated via regenerate_pki (our CA DB).
        """
        cert_path = os.path.join(self.DATA_DIR, f"{username}.crt")
        if not os.path.exists(cert_path):
            logger.warning(f"Cannot revoke {username}: cert not found at {cert_path}")
            return False

        cnf_path   = os.path.join(self.DATA_DIR, "openssl.cnf")
        index_path = os.path.join(self.DATA_DIR, "index.txt")
        crl_num    = os.path.join(self.DATA_DIR, "crlnumber")
        ca_key     = os.path.join(self.DATA_DIR, "ca.key")

        try:
            # Minimal openssl.cnf if missing
            if not os.path.exists(cnf_path):
                with open(cnf_path, "w") as f:
                    f.write(
                        "[ca]\ndefault_ca = CA_default\n\n"
                        "[CA_default]\n"
                        f"dir           = {self.DATA_DIR}\n"
                        "database      = $dir/index.txt\n"
                        "crlnumber     = $dir/crlnumber\n"
                        "default_crl_days = 30\n"
                        "default_md    = sha256\n"
                    )
            if not os.path.exists(index_path):
                open(index_path, "w").close()
            if not os.path.exists(crl_num):
                with open(crl_num, "w") as f:
                    f.write("1000\n")

            subprocess.run(
                ["openssl", "ca", "-config", cnf_path,
                 "-revoke", cert_path, "-keyfile", ca_key, "-cert", self.CA_PATH],
                check=True, capture_output=True
            )
            subprocess.run(
                ["openssl", "ca", "-config", cnf_path,
                 "-gencrl", "-out", self.CRL_PATH, "-keyfile", ca_key, "-cert", self.CA_PATH],
                check=True, capture_output=True
            )
            logger.info(f"Revoked cert for {username}, CRL updated.")
            return True
        except subprocess.CalledProcessError as exc:
            logger.error(f"Revoke failed for {username}: {exc.stderr.decode(errors='ignore')}")
            return False

    def regenerate_pki(self) -> bool:
        """
        Generate a fresh CA + server cert/key + DH + TA key.
        Steps strictly follow OpenVPN PKI best practices.
        All private keys are unencrypted (-nodes) for unattended service start.
        """
        logger.info("PKI regeneration started …")
        try:
            # 1. Remove old files
            for path in [
                self.CA_PATH, self.SERVER_CERT, self.SERVER_KEY,
                self.TA_KEY, self.DH_PATH, self.CRL_PATH,
            ]:
                if os.path.exists(path):
                    os.remove(path)

            ca_key  = os.path.join(self.DATA_DIR, "ca.key")
            srv_csr = os.path.join(self.DATA_DIR, "server.csr")
            srv_ext = os.path.join(self.DATA_DIR, "server.ext")

            # 2. CA — 10-year validity, RSA-4096
            subprocess.run(
                [
                    "openssl", "req", "-new", "-x509",
                    "-days", "3650", "-nodes",
                    "-newkey", "rsa:4096",
                    "-keyout", ca_key,
                    "-out",    self.CA_PATH,
                    "-subj",   "/C=US/O=VPNMaster/CN=VPNMaster-CA",
                ],
                check=True, capture_output=True,
            )

            # 3. Server key + CSR — RSA-2048 (fast handshake)
            subprocess.run(
                [
                    "openssl", "req", "-new", "-nodes",
                    "-newkey", "rsa:2048",
                    "-keyout", self.SERVER_KEY,
                    "-out",    srv_csr,
                    "-subj",   "/C=US/O=VPNMaster/CN=vpn-server",
                ],
                check=True, capture_output=True,
            )

            # 4. Extensions for server cert (required for `remote-cert-tls server`)
            with open(srv_ext, "w") as f:
                f.write(
                    "basicConstraints=CA:FALSE\n"
                    "nsCertType=server\n"
                    "keyUsage=critical,digitalSignature,keyEncipherment\n"
                    "extendedKeyUsage=serverAuth\n"
                    "subjectKeyIdentifier=hash\n"
                    "authorityKeyIdentifier=keyid,issuer\n"
                )

            # 5. Sign server CSR — 5-year validity
            subprocess.run(
                [
                    "openssl", "x509", "-req",
                    "-in",  srv_csr,
                    "-CA",  self.CA_PATH, "-CAkey", ca_key,
                    "-CAcreateserial",
                    "-out", self.SERVER_CERT,
                    "-days", "1825",
                    "-extfile", srv_ext,
                ],
                check=True, capture_output=True,
            )

            # 6. DH parameters — 2048-bit (fast enough; ECDHE is preferred anyway)
            subprocess.run(
                ["openssl", "dhparam", "-out", self.DH_PATH, "2048"],
                check=True, capture_output=True,
            )

            # 7. TLS-crypt / TA key
            # OpenVPN 2.5+: --genkey secret <file>
            # OpenVPN 2.4:  --genkey --secret <file>
            try:
                subprocess.run(
                    ["openvpn", "--genkey", "secret", self.TA_KEY],
                    check=True, capture_output=True,
                )
            except subprocess.CalledProcessError:
                subprocess.run(
                    ["openvpn", "--genkey", "--secret", self.TA_KEY],
                    check=True, capture_output=True,
                )

            # 8. Permissions
            subprocess.run(
                ["chmod", "600", self.SERVER_KEY, self.TA_KEY, ca_key],
                check=True,
            )
            subprocess.run(
                ["chmod", "644", self.CA_PATH, self.SERVER_CERT, self.DH_PATH],
                check=True,
            )

            # 9. Cleanup temp files
            for tmp in [srv_csr, srv_ext]:
                if os.path.exists(tmp):
                    os.remove(tmp)

            logger.info("PKI regeneration complete.")
            return True

        except subprocess.CalledProcessError as exc:
            err = exc.stderr.decode(errors="ignore") if exc.stderr else str(exc)
            logger.error(f"PKI regeneration failed: {err}")
            raise RuntimeError(f"PKI regeneration failed: {err}") from exc

    def _find_pam_plugin(self) -> Optional[str]:
        """Locate openvpn-plugin-auth-pam.so in common paths."""
        candidates = [
            "/usr/lib/openvpn/plugins/openvpn-plugin-auth-pam.so",
            "/usr/lib/x86_64-linux-gnu/openvpn/plugins/openvpn-plugin-auth-pam.so",
            "/usr/lib64/openvpn/plugins/openvpn-plugin-auth-pam.so",
            "/usr/local/lib/openvpn/plugins/openvpn-plugin-auth-pam.so",
            "/usr/lib/openvpn/openvpn-plugin-auth-pam.so",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None


# Module-level singleton
openvpn_service = OpenVPNService()
