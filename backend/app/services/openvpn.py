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

    def _load_settings(self, db=None) -> Dict[str, str]:
        """Load ovpn_* settings from DB, merged with safe hard defaults.

        If *db* is provided (e.g. an already-open SQLAlchemy Session from a
        FastAPI Depends), it is used directly to avoid opening a second
        SQLite connection on the same StaticPool.  When called from
        background tasks or standalone scripts, leave *db* as None and a
        fresh context-managed session will be created automatically.
        """
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
            "tun_mtu":            "1420",
            "mssfix":             "1380",
            # Logging & management
            "verb":           "3",
            "mute":           "20",
            "status_log":     "/var/log/openvpn/openvpn-status.log",
            "status_version": "2",
            "management":     "127.0.0.1 7505",
            # Push options
            "redirect_gateway":  "1",
            "dns":               "1.1.1.1,8.8.8.8",
            "block_outside_dns": "1",
            # Auth
            "auth_mode":    "password",
            "duplicate_cn": "0",
            # Compression (disabled by default)
            "compress":          "",
            "allow_compression": "0",
            # TLS profile
            "tls_cert_profile": "preferred",
            # Anti-censorship extras
            "client_to_client":         "0",   # canonical key (no alias needed)
            "port_share":               "",
            "block_iran_ips":           "0",
            "http_proxy_enabled":       "0",
            "http_proxy_host":          "",
            "http_proxy_port":          "80",
            "http_proxy_custom_header": "",
            "remote_address_type":      "auto",
            "remote_domain":            "",
            "remote_servers":           "",
            # Connection retry (client-side, written to client config)
            "connect_retry":            "5",
            "connect_retry_max_interval":"30",
            "connect_retry_max":        "0",
            "server_poll_timeout":      "10",
            "remote_random_hostname":   "1",
            # Push routes
            "push_routes":              "",
            "push_remove_routes":       "",
            # System
            "user":      "nobody",
            "group":     "nogroup",
            "pers_key":  "1",
            "pers_tun":  "1",
        }

        def _apply(session):
            rows = session.query(Setting).filter(Setting.key.like("ovpn_%")).all()
            for row in rows:
                key = row.key[5:]  # strip "ovpn_" prefix
                defaults[key] = row.value

        if db is not None:
            # Caller already holds a session — reuse it directly.
            _apply(db)
        else:
            # No session provided — open a short-lived one.
            from ..database import get_db_context
            with get_db_context() as session:
                _apply(session)

        # Backward compatibility with legacy key naming used in older UI builds.
        if not defaults.get("dev") and defaults.get("dev_type"):
            defaults["dev"] = defaults["dev_type"]
        if defaults.get("dev_type") and defaults.get("dev") != defaults.get("dev_type"):
            defaults["dev"] = defaults["dev_type"]

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

        proto = settings.get("protocol", "tcp")
        if proto == "udp":
            fragment = settings.get("fragment", "0")
            mssfix   = int(settings.get("mssfix", "1450"))
            if (not fragment or fragment == "0") and mssfix > 1400:
                warnings.append(
                    "UDP mode with no fragment and high mssfix may cause packet loss "
                    "on Iranian ISPs with MTU < 1500. Consider fragment=1200 or mssfix=1300."
                )

        if settings.get("tls_control_channel") in ("none", "") and proto == "tcp":
            warnings.append(
                "tls-crypt disabled on TCP/443: DPI can identify OpenVPN TLS ClientHello. "
                "Enable tls-crypt for Iran bypass."
            )

        compress = settings.get("compress", "")
        if compress and compress not in ("", "none"):
            warnings.append(
                f"Compression '{compress}' enabled. This leaks information (VORACLE attack) "
                "and makes traffic identifiable by DPI."
            )

        return warnings

    # ------------------------------------------------------------------
    # Server config generation
    # ------------------------------------------------------------------

    def generate_server_config(self, db=None) -> str:
        """Generate complete /etc/openvpn/server.conf content."""
        s = self._load_settings(db=db)
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
        conf.append(f"dev {s.get('dev') or s.get('dev_type', 'tun')}")
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
        # Certificate profile (preferred = modern ECDSA+RSA hybrid)
        tls_prof = s.get("tls_cert_profile", "preferred")
        if tls_prof and tls_prof != "preferred":
            # 'preferred' is the OpenVPN default; only emit if changed
            conf.append(f"tls-cert-profile {tls_prof}")

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

        # duplicate-cn: allow same cert from multiple devices (reduces security)
        if s.get("duplicate_cn") == "1":
            conf.append("duplicate-cn")

        # explicit-exit-notify is UDP-only
        if s.get("explicit_exit_notify", "0") != "0" and "udp" in proto:
            conf.append(f"explicit-exit-notify {s['explicit_exit_notify']}")

        # MTU tuning
        # Conservative defaults improve compatibility behind Iranian mobile/ISP paths.
        tun_mtu = s.get("tun_mtu", "1420")
        mssfix  = s.get("mssfix", "1380")
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

        # Compression — DISABLED by default (VORACLE attack; also DPI-detectable)
        # Only enable if explicitly set to a non-empty, non-"none" algorithm.
        compress_val = s.get("compress", "")
        allow_comp   = s.get("allow_compression", "0")
        if compress_val and compress_val not in ("", "none"):
            conf.append(f"compress {compress_val}")
            conf.append(f'push "compress {compress_val}"')
            conf.append("allow-compression yes")
        elif allow_comp == "1":
            # Asymmetric: server sends uncompressed, but accepts compressed from client
            conf.append("compress")
            conf.append("allow-compression asym")
        else:
            # Fully disable compression for security and lower DPI fingerprinting.
            conf.append("allow-compression no")

        # ── Anti-Censorship (Iran DPI bypass techniques) ─────────────
        conf += ["", "# ── Anti-Censorship ──────────────────────────────"]

        # Port sharing: if DPI probes port 443 with raw HTTPS, OpenVPN
        # transparently forwards to a real HTTPS backend (e.g. nginx on 8443).
        # This makes the port respond correctly to both VPN and HTTPS probes.
        port_share = s.get("port_share", "")
        if port_share:
            conf.append(f"port-share {port_share}")

        # Push socket buffer auto-tuning to clients (speeds up Iran VPS links)
        conf.append('push "sndbuf 0"')
        conf.append('push "rcvbuf 0"')

        # Block server→Iran outbound: prevent DPI from flagging our VPS as
        # "server receiving VPN that initiates Iranian IP connections".
        # We do this via iptables in a script rather than inside server.conf.
        if s.get("block_iran_ips") == "1":
            conf.append(
                "# block_iran_ips=1: add iptables rules via PostUp script or custom config"
            )

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

        # DNS push — 1.1.1.1 and 8.8.8.8 work reliably inside Iran VPN tunnels.
        # Server pushes to Windows/Android clients; client config also sets dhcp-option
        # directly for iOS/macOS compatibility.
        dns_raw = s.get("dns", "1.1.1.1,8.8.8.8")
        for dns in dns_raw.replace(",", " ").split():
            if dns.strip():
                conf.append(f'push "dhcp-option DNS {dns.strip()}"')

        # IPv6 DNS push (prevents DNS leak on dual-stack networks)
        conf.append('push "dhcp-option DNS6 2606:4700:4700::1111"')
        conf.append('push "dhcp-option DNS6 2001:4860:4860::8888"')

        # block-outside-dns: critical for Windows DNS leak protection
        if s.get("block_outside_dns", "1") == "1":
            conf.append('push "block-outside-dns"')

        # keepalive is NOT a push option — it is set directly on server.
        # The client will inherit the server's ping/ping-restart timing automatically.
        # We do push explicit ping directives so clients don't rely solely on the server:
        ping_interval = s.get("keepalive_interval", "10")
        ping_timeout  = s.get("keepalive_timeout",  "60")
        conf.append(f'push "ping {ping_interval}"')
        conf.append(f'push "ping-restart {ping_timeout}"')

        # ping-timer-rem: apply ping-restart timer from server side on client
        conf.append('push "ping-timer-rem"')

        # reneg-sec push: client re-keys at same interval — prevents asymmetric renegotiation
        _reneg = s.get("reneg_sec", "3600")
        conf.append(f'push "reneg-sec {_reneg}"')

        # Client-to-client (disabled by default — privacy)
        if s.get("client_to_client") == "1":
            conf.append("client-to-client")

        # Push additional routes to clients (e.g. LAN access)
        for route in s.get("push_routes", "").split("\n"):
            r = route.strip()
            if r:
                # Accept both "network mask" and "network/prefix" formats
                if "/" in r:
                    import ipaddress
                    try:
                        net = ipaddress.IPv4Network(r, strict=False)
                        r = f"{net.network_address} {net.netmask}"
                    except ValueError:
                        pass  # emit as-is
                conf.append(f'push "route {r}"')

        # Remove routes from client routing table (split-tunnel exclusions)
        for route in s.get("push_remove_routes", "").split("\n"):
            r = route.strip()
            if r:
                conf.append(f'push "route-del {r}"')

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
        db=None,
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
        s = self._load_settings(db=db)

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
            f"# Protocol: {remote_proto.upper()}/{remote_port}  |  Iran DPI Bypass Edition",
            "# Compatible: Android (OpenVPN for Android / Connect), iOS, Windows, macOS",
            "",
            "client",
            f"dev {s.get('dev') or s.get('dev_type', 'tun')}",
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
        if s.get("remote_random_hostname", "1") == "1" and any(c.isalpha() for c in str(remote_ip)):
            conf.append("remote-random-hostname")

        # ── Connection behaviour ──────────────────────────────────────
        conf += [
            "",
            "# ── Connection ──────────────────────────────────────────",
            "resolv-retry infinite",
            "nobind",
            "persist-key",
            "persist-tun",         # critical for Android/iOS reconnect
            "remote-cert-tls server",
            "auth-retry interact",
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
        # Legacy fallback for older OpenVPN clients that don't support data-ciphers.
        conf.append(f"cipher {s.get('data_ciphers_fallback','AES-256-GCM')}")
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
        compress_val = s.get("compress", "")
        if compress_val and compress_val not in ("", "none"):
            conf.append(f"compress {compress_val}")
            conf.append("allow-compression yes")
        elif s.get("allow_compression", "0") == "1":
            conf.append("compress stub-v2")
            conf.append("allow-compression asym")
        else:
            conf.append("allow-compression no")

        # ── MTU / MSS ─────────────────────────────────────────────────
        # These must match server-side values to avoid asymmetric MSS clamping.
        # Conservative defaults tuned for mixed Iranian ISP/mobile/NAT paths.
        # Admin can increase MTU/MSS if link quality allows.
        conf += [
            "",
            "# ── MTU / MSS (must match server) ───────────────────────",
            f"tun-mtu {s.get('tun_mtu','1420')}",
            f"mssfix  {s.get('mssfix','1380')}",
        ]
        fragment = s.get("fragment", "0")
        if fragment and fragment != "0":
            conf.append(f"fragment {fragment}")

        # Socket buffer auto-tuning (server also pushes this)
        conf += [
            "sndbuf 0",
            "rcvbuf 0",
        ]

        # ── Routing ──────────────────────────────────────────────────
        conf += [
            "",
            "# ── Routing ─────────────────────────────────────────────",
        ]
        if s.get("redirect_gateway", "1") == "1":
            conf.append("redirect-gateway def1 bypass-dhcp")

        # ── DNS ───────────────────────────────────────────────────────
        # Client-side: dhcp-option DNS is processed by the tun driver.
        # Required for Android/iOS/macOS (server push is not enough on all platforms).
        # Windows uses block-outside-dns + dhcp-option together for leak prevention.
        conf += [
            "",
            "# ── DNS (anti-leak, works on all platforms) ──────────────",
        ]
        dns_raw = s.get("dns", "1.1.1.1,8.8.8.8")
        for dns_entry in dns_raw.replace(",", " ").split():
            dns_entry = dns_entry.strip()
            if dns_entry:
                conf.append(f"dhcp-option DNS {dns_entry}")
        # IPv6 DNS (optional) — prevents DNS leak on IPv6-capable networks
        conf.append("dhcp-option DNS6 2606:4700:4700::1111")  # Cloudflare IPv6
        conf.append("dhcp-option DNS6 2001:4860:4860::8888")  # Google IPv6

        # ── Connection Timing (Iran keep-alive tuning) ────────────────
        # Iran middleboxes drop idle TCP connections after ~60-90s of inactivity.
        # ping: client sends a ping every N seconds to keep the connection alive.
        # ping-restart: restart the connection if no response in N seconds.
        # NOTE: 'keepalive' is server-only. On clients use 'ping' + 'ping-restart'.
        # The server will push "ping X" and "ping-restart Y" so these serve as
        # fallback defaults in case the server push is not received.
        ping_interval = s.get("keepalive_interval", "10")
        ping_timeout  = s.get("keepalive_timeout",  "60")
        conf += [
            "",
            "# ── Connection Timing (Iran middlebox keep-alive) ────────",
            f"ping {ping_interval}",
            f"ping-restart {ping_timeout}",
            # reneg-sec: re-key every hour. Must be <= server's reneg-sec to avoid
            # client-initiated renegotiation being rejected.
            f"reneg-sec {s.get('reneg_sec', '3600')}",
            # connect-retry: initial wait, max wait between reconnect attempts
            f"connect-retry {s.get('connect_retry', '5')} {s.get('connect_retry_max_interval', '30')}",
            # connect-retry-max: 0 = retry forever (recommended for Iran — connection drops are common)
            f"connect-retry-max {s.get('connect_retry_max', '0')}",
            # server-poll-timeout: give up on one remote and try next after N sec
            f"server-poll-timeout {s.get('server_poll_timeout', '10')}",
        ]

        # ── Platform-specific ─────────────────────────────────────────
        conf += [
            "",
            "# ── Platform-specific ───────────────────────────────────",
            # Legacy compatibility: older clients may not understand NCP keys.
            "ignore-unknown-option data-ciphers",
            "ignore-unknown-option data-ciphers-fallback",
            # Prevent unknown-option errors on clients that don't support this flag.
            "ignore-unknown-option block-outside-dns",
            # Helps OpenVPN 2.x clients parse option consistently.
            "setenv opt block-outside-dns",
            # auth-nocache: don't keep credentials in memory
            "auth-nocache",
            "",
            "# ── Logging ─────────────────────────────────────────────",
            f"verb {s.get('verb','3')}",
            "",
            "# ── Credentials ─────────────────────────────────────────",
            "auth-user-pass",       # prompt for username/password on connect
        ]

        if s.get("block_outside_dns", "1") == "1":
            # Windows DNS leak fix (ignored safely on non-Windows due to ignore-unknown-option)
            conf.insert(conf.index("# ── Logging ─────────────────────────────────────────────") - 1, "block-outside-dns")

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
