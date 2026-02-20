"""
Settings API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict

from ..database import get_db
from ..models.setting import Setting
from ..models.user import User
from ..utils.security import get_current_admin

router = APIRouter()

class SettingUpdate(BaseModel):
    value: str

@router.get("/", response_model=Dict[str, str])
async def get_settings(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all settings as key-value pairs"""
    query = db.query(Setting)
    if category:
        query = query.filter(Setting.category == category)
    
    settings = query.all()
    return {s.key: s.value for s in settings}

@router.post("/", status_code=status.HTTP_200_OK)
async def update_settings(
    settings_data: Dict[str, str],
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Update multiple settings.
    Returns changed_categories so the frontend knows which services need a restart.
    """
    changed_categories: set = set()

    for key, value in settings_data.items():
        setting = db.query(Setting).filter(Setting.key == key).first()
        if setting:
            if setting.value != str(value):   # only track actual changes
                setting.value = str(value)
                changed_categories.add(setting.category or "general")
        else:
            # Auto-register new keys
            category = "general"
            if key.startswith("ovpn_"):  category = "openvpn"
            elif key.startswith("wg_"): category = "wireguard"

            new_setting = Setting(key=key, value=str(value), category=category)
            db.add(new_setting)
            changed_categories.add(category)

    db.commit()

    # ── Auto-apply: rebuild Nginx SSL config when domain/port settings change ─
    # These keys affect Nginx config — apply changes immediately without manual intervention.
    SSL_TRIGGER_KEYS = {"panel_domain", "subscription_domain", "panel_https_port", "sub_https_port"}
    nginx_rebuild_needed = bool(SSL_TRIGGER_KEYS.intersection(settings_data.keys()))

    nginx_rebuild_result = None
    if nginx_rebuild_needed:
        import subprocess, os
        from ..models.setting import Setting as SettingModel

        def _get(key: str, default: str) -> str:
            row = db.query(SettingModel).filter(SettingModel.key == key).first()
            return row.value if row and row.value else default

        panel_domain  = _get("panel_domain", "")
        sub_domain    = _get("subscription_domain", "")
        panel_port    = _get("panel_https_port", "8443")
        sub_port      = _get("sub_https_port", "443")
        restore_script = "/opt/vpn-master-panel/restore_ssl_nginx.sh"

        results = []
        for domain, port in [(panel_domain, panel_port), (sub_domain, sub_port)]:
            if not domain or domain == sub_domain == panel_domain and domain != panel_domain:
                continue
            # Only rebuild if cert already exists — don't try to create one
            cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
            if domain and os.path.isfile(cert_path) and os.path.isfile(restore_script):
                try:
                    r = subprocess.run(
                        ["bash", restore_script, domain, port],
                        capture_output=True, text=True, timeout=30
                    )
                    if r.returncode == 0:
                        results.append(f"✓ Nginx config updated for {domain}:{port}")
                    else:
                        results.append(f"⚠ Nginx rebuild failed for {domain}: {r.stderr[:200]}")
                except Exception as exc:
                    results.append(f"⚠ Nginx rebuild error for {domain}: {exc}")
            elif domain and os.path.isfile(cert_path):
                results.append(f"ℹ {domain}: cert exists but restore script not found")
        nginx_rebuild_result = results or None

    # Build a human-readable restart hint for the frontend
    restart_hints = []
    if "openvpn" in changed_categories:
        restart_hints.append(
            "OpenVPN settings changed — click 'Generate & Apply' to write "
            "server.conf and restart the service."
        )
    if "wireguard" in changed_categories:
        restart_hints.append(
            "WireGuard settings changed — click 'Generate & Apply' to write "
            "wg0.conf and restart the service."
        )
    if nginx_rebuild_result:
        for msg in nginx_rebuild_result:
            restart_hints.append(msg)

    return {
        "message": "Settings saved successfully",
        "changed_categories": list(changed_categories),
        "restart_hints": restart_hints,
        "nginx_updated": nginx_rebuild_result,
    }

# Initialize default settings
def init_default_settings(db: Session):
    defaults = {
        # =============================================
        # OpenVPN — Iran Anti-Censorship Defaults
        # =============================================

        # ─── Network & Server ──────────────────────────────────────────
        # TCP/443: best for Iran — HTTPS port, passes most firewalls and DPI
        "ovpn_protocol":        "tcp",
        "ovpn_port":            "443",
        "ovpn_dev":             "tun",
        "ovpn_dev_type":        "tun",
        "ovpn_topology":        "subnet",
        "ovpn_server_subnet":   "10.8.0.0",
        "ovpn_server_netmask":  "255.255.255.0",
        "ovpn_max_clients":     "100",
        "ovpn_server_ip":       "",            # Override detected public IP

        # ─── Connectivity & Reliability ────────────────────────────────
        "ovpn_keepalive_interval": "10",
        "ovpn_keepalive_timeout":  "60",
        "ovpn_float":              "1",        # Allow client IP to float (mobile networks)
        "ovpn_pers_tun":           "1",
        "ovpn_pers_key":           "1",
        "ovpn_user":               "nobody",
        "ovpn_group":              "nogroup",

        # ─── Timeouts ──────────────────────────────────────────────────
        "ovpn_reneg_sec":            "3600",
        "ovpn_hand_window":          "60",
        "ovpn_tran_window":          "3600",
        "ovpn_tls_timeout":          "2",
        "ovpn_connect_retry":        "5",
        "ovpn_connect_retry_max":    "0",
        "ovpn_server_poll_timeout":  "10",
        # explicit-exit-notify is UDP-only; omit for TCP (will be ignored anyway)
        "ovpn_explicit_exit_notify": "0",

        # ─── Cryptography & Security ───────────────────────────────────
        # NOTE: ovpn_cipher is removed — use ovpn_data_ciphers (NCP negotiation, OpenVPN 2.4+)
        "ovpn_data_ciphers":         "AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305",
        "ovpn_data_ciphers_fallback":"AES-256-GCM",
        "ovpn_auth_digest":          "SHA256",
        "ovpn_tls_version_min":      "1.2",
        "ovpn_tls_cert_profile":     "preferred",
        # TLS 1.2 cipher suites — match modern HTTPS browser fingerprint
        "ovpn_tls_ciphers": (
            "TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384:"
            "TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384:"
            "TLS-ECDHE-ECDSA-WITH-CHACHA20-POLY1305-SHA256:"
            "TLS-ECDHE-RSA-WITH-CHACHA20-POLY1305-SHA256"
        ),
        # TLS 1.3 cipher suites (OpenVPN 2.5+)
        "ovpn_tls_cipher_suites":    "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256",
        "ovpn_ecdh_curve":           "secp384r1",
        "ovpn_dh_file":              "none",   # Pure ECDHE — no static DH needed
        "ovpn_crl_verify":           "crl.pem",

        # ─── TLS Control Channel (Iran DPI bypass core) ─────────────────
        # tls-crypt wraps the entire TLS handshake in an HMAC envelope,
        # making it indistinguishable from random data to DPI.
        "ovpn_tls_control_channel":  "tls-crypt",
        "ovpn_auth_nocache":         "1",

        # ─── MTU / MSS — TCP/443 over Ethernet ─────────────────────────
        # tun-mtu 1500: full Ethernet MTU; mssfix 1450 leaves room for
        # OpenVPN+TLS headers when running TCP-in-TCP (TCP/443).
        "ovpn_tun_mtu":   "1500",
        "ovpn_mssfix":    "1450",
        "ovpn_fragment":  "0",       # Fragment not needed for TCP; use for UDP only
        # NOTE: mtu-test/mtu-disc removed — unreliable through Iran NAT, breaks TCP/443

        # ─── Routing & DNS ──────────────────────────────────────────────
        "ovpn_redirect_gateway":   "1",
        "ovpn_dns":                "1.1.1.1,8.8.8.8",
        "ovpn_block_outside_dns":  "1",    # Windows DNS leak protection — ENABLED
        # Client-to-client: one canonical key used by both UI and backend
        "ovpn_client_to_client":   "0",
        "ovpn_push_routes":        "",
        "ovpn_push_remove_routes": "",

        # ─── Logging & Management ──────────────────────────────────────
        "ovpn_verb":           "3",
        "ovpn_mute":           "20",
        "ovpn_status_log":     "/var/log/openvpn/openvpn-status.log",
        "ovpn_status_version": "2",          # CLIENT_LIST format for monitoring.py
        "ovpn_management":     "127.0.0.1 7505",

        # ─── Authentication ─────────────────────────────────────────────
        "ovpn_auth_mode":    "password",    # password | cert | 2fa
        "ovpn_duplicate_cn": "0",           # allow same cert from multiple devices

        # ─── Compression ────────────────────────────────────────────────
        "ovpn_compress":          "",        # DISABLED — VORACLE + DPI risk
        "ovpn_allow_compression": "0",       # whether to allow client-initiated compression

        # ─── HTTP Proxy / Domain Fronting (native OpenVPN) ───────────────
        # Lets OpenVPN Connect route through an HTTP CONNECT proxy with a
        # spoofed Host header — effective against Iran SNI filtering.
        "ovpn_http_proxy_enabled":       "0",
        "ovpn_http_proxy_host":          "",   # Proxy IP / CDN edge IP
        "ovpn_http_proxy_port":          "80",
        "ovpn_http_proxy_custom_header": "",   # Spoofed Host domain for DPI bypass

        # ─── Multi-Remote Failover ──────────────────────────────────────
        "ovpn_remote_servers":       "",   # "ip:port:proto,ip:port:proto"
        "ovpn_remote_address_type":  "auto",   # auto | custom_ip | domain
        "ovpn_remote_domain":        "",       # custom domain for clients

        # ─── Port Sharing (HTTPS camouflage) ────────────────────────────
        # Forward non-VPN probes on port 443 to a real HTTPS server.
        # e.g. "127.0.0.1 8443"
        "ovpn_port_share": "",

        # ─── Block Iranian IPs (server-side) ────────────────────────────
        # Script-based — see custom_server_config for iptables rules
        "ovpn_block_iran_ips": "0",

        # ─── Custom Config Append ──────────────────────────────────────
        "ovpn_custom_client_config": "",
        "ovpn_custom_server_config": "",

        # ─── General panel settings ─────────────────────────────────────
        "panel_domain":        "",         # Admin panel domain (proxy ON)
        "ssl_email":           "",         # Email for Let's Encrypt alerts

        # HTTPS port for the admin panel.
        # Default: 8443 — because OpenVPN uses port 443 (Iran anti-censorship TCP/443).
        # Change to 443 only if OpenVPN is configured on a different port.
        # The backend also auto-detects port conflicts at SSL issuance time.
        "panel_https_port":    "8443",

        # HTTPS port for the subscription endpoint.
        # Default: 443 — subscription does not conflict with OpenVPN
        # (OpenVPN binds to the OpenVPN service, not Nginx port 443).
        # Change to 8444 or another port if you have a different service on 443.
        "sub_https_port":      "443",

        # =============================================
        # WireGuard — Iran Anti-Censorship Defaults
        # =============================================

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

        # WARP Integration
        "wg_warp_enabled": "0",
        "wg_warp_mode": "proxy",
        "wg_block_iran_ips": "0",

        # Server
        "wg_endpoint_ip": "",

        # Advanced
        "wg_custom_client_config": "",
        "wg_custom_server_config": "",

        # =============================================
        # General — Panel Features
        # =============================================
        "admin_contact": "",

        # Subscription Links (3x-ui/Marzban/Hiddify-style)
        "subscription_enabled": "0",
        "subscription_domain": "",
        "subscription_format": "v2ray",
        "subscription_update_interval": "24",
        "config_export_qr": "1",
        "config_export_uri": "1",

        # Telegram Bot Integration
        "telegram_enabled": "0",
        "telegram_bot_token": "",
        "telegram_admin_chat_id": "",
        "telegram_notify_user_created": "1",
        "telegram_notify_user_expired": "1",
        "telegram_notify_traffic_warning": "1",
        "telegram_notify_server_down": "1",
        "telegram_auto_backup": "0",

        # Smart Proxy (Hiddify-style)
        "smart_proxy_enabled": "0",
        "smart_proxy_mode": "bypass_iran",
        "smart_proxy_bypass_domains": "",
        "smart_proxy_bypass_ips": "",

        # Periodic Traffic Limits (Marzban-style)
        "periodic_traffic_enabled": "0",
        "periodic_traffic_type": "monthly",
        "periodic_traffic_reset_day": "1",
        "traffic_exceed_action": "suspend",
        "traffic_warning_percent": "80",
    }
    
    # Fetch all existing keys in a single query to avoid N+1 on every startup.
    existing_keys = {row.key for row in db.query(Setting.key).all()}

    new_settings = []
    for key, value in defaults.items():
        if key not in existing_keys:
            category = "general"
            if key.startswith("ovpn_"):
                category = "openvpn"
            elif key.startswith("wg_"):
                category = "wireguard"
            new_settings.append(Setting(key=key, value=value, category=category))

    if new_settings:
        db.bulk_save_objects(new_settings)
        db.commit()


# =============================================
# PKI Management
# =============================================

@router.post("/pki/regenerate", status_code=status.HTTP_200_OK)
async def regenerate_pki(
    current_admin: User = Depends(get_current_admin)
):
    """Regenerate OpenVPN CA and Server Certificates"""
    from ..services.openvpn import openvpn_service
    try:
        openvpn_service.regenerate_pki()
        return {"message": "PKI regenerated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pki/info")
async def get_pki_info(
    current_admin: User = Depends(get_current_admin)
):
    """Get CA certificate information"""
    from ..services.openvpn import openvpn_service
    return openvpn_service.get_ca_info()


# =============================================
# Server Config Preview & Apply
# =============================================

@router.get("/server-config/preview")
async def preview_server_config(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Preview the generated OpenVPN server.conf (includes validation warnings)"""
    from ..services.openvpn import openvpn_service
    try:
        s        = openvpn_service._load_settings(db=db)
        config   = openvpn_service.generate_server_config(db=db)
        warnings = openvpn_service.validate_config(s)
        return {"content": config, "filename": "server.conf", "warnings": warnings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/server-config/apply")
async def apply_server_config(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Generate and write server.conf to /etc/openvpn/server.conf"""
    from ..services.openvpn import openvpn_service
    import os

    try:
        config = openvpn_service.generate_server_config(db=db)

        # Write to standard OpenVPN location
        config_path = "/etc/openvpn/server.conf"

        # Also save a copy in our data dir
        backup_path = os.path.join(openvpn_service.DATA_DIR, "server.conf")
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)

        with open(backup_path, "w") as f:
            f.write(config)

        # Try to write to system path (may need root)
        try:
            # SAFETY CHECK: Ensure we are NOT overwriting keys
            if "BEGIN PRIVATE KEY" in config:
                raise ValueError("Security violation: Attempted to write private key to server.conf")

            with open(config_path, "w") as f:
                f.write(config)
            system_written = True

            # Auto-Restart Service
            try:
                import subprocess
                subprocess.run(["systemctl", "restart", "openvpn@server"], check=True)
                restart_status = "Service restarted successfully."
            except Exception as e:
                restart_status = f"Service restart failed: {str(e)}"

        except PermissionError:
            system_written = False
            restart_status = "Permission denied: Cannot write to system path."

        # Include validation warnings in the response
        s = openvpn_service._load_settings(db=db)
        warnings = openvpn_service.validate_config(s)

        return {
            "message": "Server config generated",
            "system_path": config_path if system_written else None,
            "backup_path": backup_path,
            "system_written": system_written,
            "restart_status": restart_status,
            "warnings": warnings,
            "hint": "Configuration applied." if system_written else
                    f"Copy manually: sudo cp {backup_path} {config_path} && sudo systemctl restart openvpn@server"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/openvpn/version")
async def get_openvpn_version(
    current_admin: User = Depends(get_current_admin)
):
    """Get OpenVPN version installed on system"""
    import subprocess
    try:
        result = subprocess.run(
            ["openvpn", "--version"],
            capture_output=True, text=True, timeout=5
        )
        # openvpn --version exits with code 1 but still prints to stdout
        output = (result.stdout or result.stderr or "").strip()
        first_line = output.splitlines()[0] if output else ""
        return {"version": first_line or "Unknown"}
    except FileNotFoundError:
        return {"version": "Not Installed"}
    except Exception as exc:
        return {"version": f"Error: {exc}"}


# =============================================
# WireGuard Server Config, Keys & Status
# =============================================

@router.get("/wg-server-config/preview")
async def preview_wg_server_config(
    current_admin: User = Depends(get_current_admin)
):
    """Preview the generated WireGuard wg0.conf"""
    from ..services.wireguard import wireguard_service
    try:
        config = wireguard_service.generate_server_config()
        return {"content": config, "filename": "wg0.conf"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wg-server-config/apply")
async def apply_wg_server_config(
    current_admin: User = Depends(get_current_admin)
):
    """Generate and write wg0.conf to /etc/wireguard/"""
    from ..services.wireguard import wireguard_service
    import os

    try:
        config = wireguard_service.generate_server_config()
        settings = wireguard_service._load_settings()
        interface = settings.get("wg_interface", "wg0")

        config_path = f"/etc/wireguard/{interface}.conf"
        backup_path = os.path.join(wireguard_service.DATA_DIR, f"{interface}.conf")
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)

        with open(backup_path, "w") as f:
            f.write(config)

        try:
            with open(config_path, "w") as f:
                f.write(config)
            system_written = True
        except PermissionError:
            system_written = False

        return {
            "message": "WireGuard server config generated",
            "system_path": config_path if system_written else None,
            "backup_path": backup_path,
            "system_written": system_written,
            "hint": f"Run 'sudo wg-quick down {interface} && sudo wg-quick up {interface}' to apply" if system_written else
                    f"Copy manually: sudo cp {backup_path} {config_path} && sudo wg-quick up {interface}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wg-status")
async def get_wg_status(
    current_admin: User = Depends(get_current_admin)
):
    """Get WireGuard interface status and all peer stats"""
    from ..services.wireguard import wireguard_service
    return wireguard_service.get_interface_status()


@router.post("/wg-keys/regenerate")
async def regenerate_wg_keys(
    current_admin: User = Depends(get_current_admin)
):
    """Regenerate WireGuard server keypair"""
    from ..services.wireguard import wireguard_service
    try:
        keys = wireguard_service.regenerate_server_keys()
        return {
            "message": "WireGuard server keys regenerated",
            "public_key": keys["public_key"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wg-obfuscation/script")
async def get_obfuscation_script(
    current_admin: User = Depends(get_current_admin)
):
    """Get server-side obfuscation setup script"""
    from ..services.wireguard import wireguard_service
    script = wireguard_service.generate_obfuscation_setup_script()
    return {"content": script, "filename": "setup_obfuscation.sh"}

# =============================================
# Panel SSL Management (Certbot)
# =============================================

class SSLRequest(BaseModel):
    domain: str
    email: str
    https_port: Optional[int] = None  # None = auto-detect; 443 or 8443 = explicit

@router.post("/ssl/request")
async def request_letsencrypt_ssl(
    req: SSLRequest,
    current_admin: User = Depends(get_current_admin)
):
    """
    Issue a Let's Encrypt SSL certificate for a domain.
    Streams live certbot output so the UI can display progress in real time.

    IMPORTANT — async wrapper:
      ssl_service.stream_letsencrypt_cert() is a *synchronous* generator
      (it calls subprocess.Popen and reads lines in a tight loop).
      We wrap it in an async generator that delegates to a thread pool via
      asyncio.to_thread / run_in_executor so the event loop is never blocked
      and FastAPI can flush each chunk immediately without buffering.

    Headers:
      X-Accel-Buffering: no   → Nginx: disable proxy_buffering for this response
      Cache-Control: no-cache → no intermediary caching
      Connection: keep-alive  → keep the TCP connection alive during long cert issuance
    """
    import asyncio
    from ..services.ssl_service import SSLService

    ssl_service = SSLService()

    # Resolve https_port: use caller-supplied value if present, else None (auto-detect)
    https_port_arg = req.https_port if req.https_port in (443, 8443, 8444) else None

    headers = {
        "X-Accel-Buffering": "no",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Transfer-Encoding": "chunked",
    }

    async def _async_stream():
        """
        Bridge between the synchronous SSLService generator and FastAPI's
        async StreamingResponse.  Each chunk is yielded immediately so the
        browser sees live output without waiting for certbot to finish.
        """
        loop = asyncio.get_event_loop()
        sync_gen = ssl_service.stream_letsencrypt_cert(req.domain, req.email, https_port_arg)

        while True:
            # Run the next() call of the sync generator in a thread so the
            # event loop stays responsive and Nginx keep-alive ticks work.
            chunk = await loop.run_in_executor(
                None, lambda g=sync_gen: next(g, None)
            )
            if chunk is None:
                break
            yield chunk.encode("utf-8")

    return StreamingResponse(
        _async_stream(),
        media_type="text/plain; charset=utf-8",
        headers=headers,
    )


@router.get("/ssl/status")
async def get_ssl_status(
    domain: str,
    current_admin: User = Depends(get_current_admin)
):
    """Check the SSL certificate status for a domain."""
    from ..services.ssl_service import SSLService
    ssl_service = SSLService()
    return ssl_service.check_ssl_status(domain)
